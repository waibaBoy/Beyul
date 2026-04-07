from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from uuid import UUID

import httpx
from eth_abi import decode, encode
from eth_account import Account
from eth_utils import keccak, to_checksum_address

from app.core.config import settings

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ZERO_BYTES32 = b"\x00" * 32
ASSERT_TRUTH_SIGNATURE = "assertTruth(bytes,address,address,address,uint64,address,uint256,bytes32,bytes32)"
GET_ASSERTION_SIGNATURE = "getAssertion(bytes32)"
ASSERTION_MADE_EVENT_SIGNATURE = (
    "AssertionMade(bytes32,bytes32,bytes,address,address,address,address,uint64,address,uint256,bytes32)"
)
ASSERT_TRUTH_SELECTOR = keccak(text=ASSERT_TRUTH_SIGNATURE)[:4]
GET_ASSERTION_SELECTOR = keccak(text=GET_ASSERTION_SIGNATURE)[:4]
ASSERTION_MADE_EVENT_TOPIC = "0x" + keccak(text=ASSERTION_MADE_EVENT_SIGNATURE).hex()


@dataclass(frozen=True)
class OracleResolutionRequest:
    market_id: UUID
    market_slug: str
    candidate_id: UUID
    resolution_mode: str
    source_reference_url: str | None
    notes: str | None
    finalizes_at: datetime | None


@dataclass(frozen=True)
class OracleResolutionStatusRequest:
    market_id: UUID
    market_slug: str
    candidate_id: UUID
    current_payload: dict[str, object]


class OracleService:
    async def begin_resolution(self, request: OracleResolutionRequest) -> dict[str, object]:
        raise NotImplementedError

    async def reconcile_resolution(self, request: OracleResolutionStatusRequest) -> dict[str, object]:
        raise NotImplementedError

    async def get_live_readiness(self) -> dict[str, object]:
        raise NotImplementedError

    async def approve_bond_allowance(self, amount_wei: str | None = None) -> dict[str, object]:
        raise NotImplementedError


class OracleConfigurationError(RuntimeError):
    pass


def _build_common_metadata(request: OracleResolutionRequest) -> dict[str, object]:
    liveness_minutes = settings.oracle_liveness_minutes
    liveness_seconds = liveness_minutes * 60
    return {
        "market_slug": request.market_slug,
        "status": "pending_oracle",
        "source_reference_url": request.source_reference_url,
        "finalizes_at": request.finalizes_at.isoformat() if request.finalizes_at else None,
        "chain_id": settings.oracle_chain_id,
        "reward_wei": settings.oracle_reward_wei,
        "bond_wei": settings.oracle_bond_wei,
        "liveness_minutes": liveness_minutes,
        "liveness_seconds": liveness_seconds,
        "currency_address": settings.oracle_currency_address or None,
        "execution_mode": settings.oracle_execution_mode,
    }


def _build_uma_claim(request: OracleResolutionRequest) -> str:
    source_reference = request.source_reference_url or "unspecified source"
    return (
        f"Market {request.market_slug} with candidate {request.candidate_id} resolves according to the configured "
        f"settlement source at {source_reference}. The proposed oracle outcome should be treated as truthful if and only "
        f"if the external resolution data unambiguously supports the submitted winner."
    )


def _mask_private_value(value: str | None) -> str | None:
    if not value:
        return None
    trimmed = value.strip()
    if len(trimmed) <= 10:
        return trimmed
    return f"{trimmed[:6]}...{trimmed[-4:]}"


def _strip_0x(value: str) -> str:
    return value[2:] if value.startswith("0x") else value


def _to_bytes32(value: str) -> bytes:
    raw = value.encode("utf-8")
    if len(raw) > 32:
        raise OracleConfigurationError(f"UMA bytes32 value is too long: {value}")
    return raw.ljust(32, b"\x00")


def _bytes32_hex(value: bytes | str) -> str:
    raw = value if isinstance(value, bytes) else bytes.fromhex(_strip_0x(value))
    if len(raw) != 32:
        raise OracleConfigurationError("UMA bytes32 values must be 32 bytes long")
    return "0x" + raw.hex()


def _decode_bytes32_text(value: bytes | str) -> str:
    raw = value if isinstance(value, bytes) else bytes.fromhex(_strip_0x(value))
    return raw.rstrip(b"\x00").decode("utf-8", errors="ignore")


def _normalize_address(value: str | None, *, field_name: str, allow_zero: bool = False) -> str:
    if not value:
        if allow_zero:
            return ZERO_ADDRESS
        raise OracleConfigurationError(f"{field_name} is required for UMA live execution")
    normalized = to_checksum_address(value)
    if normalized == ZERO_ADDRESS and not allow_zero:
        raise OracleConfigurationError(f"{field_name} cannot be the zero address")
    return normalized


def _coerce_int(value: object, *, field_name: str) -> int:
    if isinstance(value, bool):
        raise OracleConfigurationError(f"{field_name} must be numeric")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            raise OracleConfigurationError(f"{field_name} must not be empty")
        return int(trimmed, 16) if trimmed.startswith("0x") else int(trimmed)
    raise OracleConfigurationError(f"{field_name} must be numeric")


def _isoformat_unix_timestamp(value: int | None) -> str | None:
    if value is None or value <= 0:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


def _extract_rpc_error(error_body: object) -> str:
    if not isinstance(error_body, dict):
        return str(error_body)
    details = error_body.get("error")
    if isinstance(details, dict):
        message = details.get("message")
        data = details.get("data")
        if isinstance(data, dict):
            nested_message = data.get("message")
            if isinstance(nested_message, str) and nested_message.strip():
                return nested_message
        if isinstance(data, str) and data.strip():
            return data
        if isinstance(message, str) and message.strip():
            return message
    return str(error_body)


def _derive_onchain_assertion_state(*, settled: bool, settlement_resolution: bool, disputer: str | None) -> str:
    normalized_disputer = disputer or ZERO_ADDRESS
    if settled:
        return "settled_true" if settlement_resolution else "settled_false"
    if normalized_disputer != ZERO_ADDRESS:
        return "disputed"
    return "asserted"


def _build_assert_truth_calldata(
    *,
    claim: str,
    asserter: str,
    callback_recipient: str,
    escalation_manager: str,
    liveness_seconds: int,
    currency: str,
    bond_wei: int,
    identifier: str,
    domain_id: bytes,
) -> str:
    encoded_args = encode(
        ["bytes", "address", "address", "address", "uint64", "address", "uint256", "bytes32", "bytes32"],
        [
            claim.encode("utf-8"),
            asserter,
            callback_recipient,
            escalation_manager,
            liveness_seconds,
            currency,
            bond_wei,
            _to_bytes32(identifier),
            domain_id,
        ],
    )
    return "0x" + (ASSERT_TRUTH_SELECTOR + encoded_args).hex()


def _build_get_assertion_calldata(assertion_id: str) -> str:
    encoded_args = encode(["bytes32"], [bytes.fromhex(_strip_0x(assertion_id))])
    return "0x" + (GET_ASSERTION_SELECTOR + encoded_args).hex()


def _decode_assertion_id(raw_result: str) -> str:
    payload = bytes.fromhex(_strip_0x(raw_result))
    (assertion_id,) = decode(["bytes32"], payload)
    return _bytes32_hex(assertion_id)


def _decode_assertion_state(raw_result: str) -> dict[str, object]:
    payload = bytes.fromhex(_strip_0x(raw_result))
    ((escalation_settings, asserter, assertion_time, settled, currency, expiration_time, settlement_resolution, domain_id, identifier, bond, callback_recipient, disputer),) = decode(
        ["((bool,bool,bool,address,address),address,uint64,bool,address,uint64,bool,bytes32,bytes32,uint256,address,address)"],
        payload,
    )
    arbitrate_via_em, discard_oracle, validate_disputers, asserting_caller, escalation_manager = escalation_settings
    normalized_disputer = str(disputer)
    return {
        "assertion_asserter": str(asserter),
        "assertion_time_unix": int(assertion_time),
        "assertion_time": _isoformat_unix_timestamp(int(assertion_time)),
        "assertion_settled": bool(settled),
        "assertion_currency_address": str(currency),
        "assertion_expiration_time_unix": int(expiration_time),
        "assertion_expiration_time": _isoformat_unix_timestamp(int(expiration_time)),
        "assertion_resolution": bool(settlement_resolution),
        "assertion_domain_id": _bytes32_hex(domain_id),
        "assertion_identifier": _decode_bytes32_text(identifier) or _bytes32_hex(identifier),
        "assertion_identifier_hex": _bytes32_hex(identifier),
        "assertion_bond_wei": str(bond),
        "assertion_callback_recipient": str(callback_recipient),
        "assertion_disputer": normalized_disputer,
        "assertion_disputed": normalized_disputer != ZERO_ADDRESS,
        "assertion_escalation_settings": {
            "arbitrate_via_escalation_manager": bool(arbitrate_via_em),
            "discard_oracle": bool(discard_oracle),
            "validate_disputers": bool(validate_disputers),
            "asserting_caller": str(asserting_caller),
            "escalation_manager": str(escalation_manager),
        },
        "onchain_assertion_state": _derive_onchain_assertion_state(
            settled=bool(settled),
            settlement_resolution=bool(settlement_resolution),
            disputer=normalized_disputer,
        ),
    }


def _build_erc20_read_calldata(signature: str, argument_types: list[str], args: list[object]) -> str:
    selector = keccak(text=signature)[:4]
    encoded_args = encode(argument_types, args) if argument_types else b""
    return "0x" + (selector + encoded_args).hex()


def _build_erc20_approve_calldata(spender: str, amount_wei: int) -> str:
    return _build_erc20_read_calldata(
        "approve(address,uint256)",
        ["address", "uint256"],
        [spender, amount_wei],
    )


def _decode_uint256_result(raw_result: str) -> int:
    payload = bytes.fromhex(_strip_0x(raw_result))
    (value,) = decode(["uint256"], payload)
    return int(value)


def _extract_assertion_id_from_receipt(receipt: dict[str, object]) -> str | None:
    logs = receipt.get("logs")
    if not isinstance(logs, list):
        return None
    for raw_log in logs:
        if not isinstance(raw_log, dict):
            continue
        topics = raw_log.get("topics")
        if not isinstance(topics, list) or len(topics) < 2:
            continue
        topic0 = topics[0] if isinstance(topics[0], str) else None
        topic1 = topics[1] if isinstance(topics[1], str) else None
        if topic0 and topic0.lower() == ASSERTION_MADE_EVENT_TOPIC.lower() and topic1:
            return _bytes32_hex(topic1)
    return None


def _build_common_live_payload(request: OracleResolutionRequest, *, signer_address: str | None) -> dict[str, object]:
    return {
        "assertion_method": "assertTruth",
        "assertion_identifier": settings.oracle_uma_assertion_identifier,
        "assertion_claim": _build_uma_claim(request),
        "oracle_contract_address": settings.oracle_uma_oo_address or None,
        "finder_address": settings.oracle_uma_finder_address or None,
        "escalation_manager": settings.oracle_uma_escalation_manager or None,
        "signer_address": signer_address,
        "tx_hash": None,
        "simulated_submission": settings.oracle_execution_mode != "live",
        **_build_common_metadata(request),
    }


class _JsonRpcClient:
    def __init__(self, rpc_url: str) -> None:
        self._rpc_url = rpc_url
        self._request_id = 0

    async def request(self, method: str, params: list[object]) -> object:
        self._request_id += 1
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    self._rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": self._request_id,
                        "method": method,
                        "params": params,
                    },
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OracleConfigurationError(f"UMA live RPC call failed for {method}: {exc}") from exc

        body = response.json()
        if "error" in body:
            raise OracleConfigurationError(f"UMA RPC {method} failed: {_extract_rpc_error(body)}")
        return body.get("result")


class MockOracleService(OracleService):
    async def begin_resolution(self, request: OracleResolutionRequest) -> dict[str, object]:
        return {
            "provider": "mock_oracle",
            "provider_kind": "optimistic",
            "network": "offchain-dev",
            "assertion_id": str(request.candidate_id),
            **_build_common_metadata(request),
        }

    async def reconcile_resolution(self, request: OracleResolutionStatusRequest) -> dict[str, object]:
        payload = dict(request.current_payload)
        if "submission_status" not in payload:
            payload["submission_status"] = "simulated"
        payload["last_reconciled_at"] = datetime.now(timezone.utc).isoformat()
        return payload

    async def get_live_readiness(self) -> dict[str, object]:
        return {
            "provider": "mock_oracle",
            "execution_mode": settings.oracle_execution_mode,
            "network": "offchain-dev",
            "chain_id": settings.oracle_chain_id,
            "rpc_chain_id": None,
            "signer_address": settings.oracle_signer_address or None,
            "oracle_contract_address": settings.oracle_uma_oo_address or None,
            "currency_address": settings.oracle_currency_address or None,
            "native_balance_wei": None,
            "token_balance_wei": None,
            "allowance_wei": None,
            "required_bond_wei": settings.oracle_bond_wei,
            "reward_wei": settings.oracle_reward_wei,
            "liveness_minutes": settings.oracle_liveness_minutes,
            "approval_required": False,
            "ready_for_live_submission": settings.oracle_execution_mode != "live",
            "issues": ["Mock oracle does not use onchain signer readiness checks."],
            "tx_preview": {},
        }

    async def approve_bond_allowance(self, amount_wei: str | None = None) -> dict[str, object]:
        return {
            "provider": "mock_oracle",
            "execution_mode": settings.oracle_execution_mode,
            "status": "not_applicable",
            "chain_id": settings.oracle_chain_id,
            "signer_address": settings.oracle_signer_address or None,
            "spender_address": settings.oracle_uma_oo_address or None,
            "currency_address": settings.oracle_currency_address or None,
            "amount_wei": amount_wei or settings.oracle_bond_wei,
            "allowance_before_wei": "0",
            "tx_hash": None,
            "submission_status": "not_applicable",
            "nonce": None,
            "gas_limit": None,
            "gas_price_wei": None,
        }


class UMAOracleService(OracleService):
    def _build_assertion_payload(
        self,
        request: OracleResolutionRequest,
        *,
        signer_address: str | None,
    ) -> dict[str, object]:
        return {
            "provider": "uma_optimistic_oracle_v3",
            "provider_kind": "optimistic",
            "network": "polygon" if settings.oracle_chain_id == 137 else f"chain-{settings.oracle_chain_id}",
            **_build_common_live_payload(request, signer_address=signer_address),
        }

    def _resolve_live_signer(self) -> tuple[str, str]:
        if not settings.oracle_signer_private_key:
            raise OracleConfigurationError("ORACLE_SIGNER_PRIVATE_KEY is required for UMA live execution")
        account = Account.from_key(settings.oracle_signer_private_key)
        derived_address = to_checksum_address(account.address)
        configured_address = settings.oracle_signer_address
        if configured_address:
            normalized_configured = _normalize_address(
                configured_address,
                field_name="ORACLE_SIGNER_ADDRESS",
                allow_zero=False,
            )
            if normalized_configured != derived_address:
                raise OracleConfigurationError(
                    f"ORACLE_SIGNER_ADDRESS does not match the configured private key ({derived_address})"
                )
        return derived_address, settings.oracle_signer_private_key

    async def _build_live_rpc_context(self) -> tuple[_JsonRpcClient, int]:
        if not settings.oracle_rpc_url:
            raise OracleConfigurationError("ORACLE_RPC_URL is required for UMA live execution")
        rpc = _JsonRpcClient(settings.oracle_rpc_url)
        rpc_chain_hex = await rpc.request("eth_chainId", [])
        if not isinstance(rpc_chain_hex, str):
            raise OracleConfigurationError("UMA live execution could not read eth_chainId from the configured RPC.")
        rpc_chain_id = int(rpc_chain_hex, 16)
        if rpc_chain_id != settings.oracle_chain_id:
            raise OracleConfigurationError(
                f"UMA live execution RPC chain mismatch: expected {settings.oracle_chain_id}, got {rpc_chain_id}"
            )
        return rpc, rpc_chain_id

    async def _read_uint256(
        self,
        rpc: _JsonRpcClient,
        *,
        contract_address: str,
        signature: str,
        argument_types: list[str],
        args: list[object],
    ) -> int:
        result = await rpc.request(
            "eth_call",
            [
                {
                    "to": contract_address,
                    "data": _build_erc20_read_calldata(signature, argument_types, args),
                },
                "latest",
            ],
        )
        if not isinstance(result, str):
            raise OracleConfigurationError(f"{signature} returned an unexpected payload")
        return _decode_uint256_result(result)

    async def get_live_readiness(self) -> dict[str, object]:
        base_payload = {
            "provider": "uma_optimistic_oracle_v3",
            "execution_mode": settings.oracle_execution_mode,
            "network": "polygon" if settings.oracle_chain_id == 137 else f"chain-{settings.oracle_chain_id}",
            "chain_id": settings.oracle_chain_id,
            "rpc_chain_id": None,
            "signer_address": settings.oracle_signer_address or None,
            "oracle_contract_address": settings.oracle_uma_oo_address or None,
            "currency_address": settings.oracle_currency_address or None,
            "native_balance_wei": None,
            "token_balance_wei": None,
            "allowance_wei": None,
            "required_bond_wei": settings.oracle_bond_wei,
            "reward_wei": settings.oracle_reward_wei,
            "liveness_minutes": settings.oracle_liveness_minutes,
            "approval_required": False,
            "ready_for_live_submission": False,
            "issues": [],
            "tx_preview": {},
        }
        if settings.oracle_execution_mode != "live":
            base_payload["issues"] = ["Oracle execution mode is simulated. Switch to live after signer readiness passes."]
            base_payload["ready_for_live_submission"] = True
            return base_payload

        issues: list[str] = []
        try:
            signer_address, _ = self._resolve_live_signer()
            base_payload["signer_address"] = signer_address
        except OracleConfigurationError as exc:
            issues.append(str(exc))
            signer_address = None

        try:
            oo_address = _normalize_address(settings.oracle_uma_oo_address, field_name="ORACLE_UMA_OO_ADDRESS")
            currency_address = _normalize_address(
                settings.oracle_currency_address,
                field_name="ORACLE_CURRENCY_ADDRESS",
            )
            base_payload["oracle_contract_address"] = oo_address
            base_payload["currency_address"] = currency_address
        except OracleConfigurationError as exc:
            issues.append(str(exc))
            oo_address = None
            currency_address = None

        bond_wei = _coerce_int(settings.oracle_bond_wei, field_name="ORACLE_BOND_WEI")
        base_payload["required_bond_wei"] = str(bond_wei)
        base_payload["reward_wei"] = str(_coerce_int(settings.oracle_reward_wei, field_name="ORACLE_REWARD_WEI"))

        try:
            rpc, rpc_chain_id = await self._build_live_rpc_context()
            base_payload["rpc_chain_id"] = rpc_chain_id
        except OracleConfigurationError as exc:
            issues.append(str(exc))
            base_payload["issues"] = issues
            return base_payload

        if signer_address and currency_address and oo_address:
            native_balance_hex = await rpc.request("eth_getBalance", [signer_address, "latest"])
            if not isinstance(native_balance_hex, str):
                raise OracleConfigurationError("eth_getBalance returned an unexpected payload")
            native_balance = _coerce_int(native_balance_hex, field_name="eth_getBalance")
            token_balance = await self._read_uint256(
                rpc,
                contract_address=currency_address,
                signature="balanceOf(address)",
                argument_types=["address"],
                args=[signer_address],
            )
            allowance = await self._read_uint256(
                rpc,
                contract_address=currency_address,
                signature="allowance(address,address)",
                argument_types=["address", "address"],
                args=[signer_address, oo_address],
            )
            base_payload["native_balance_wei"] = str(native_balance)
            base_payload["token_balance_wei"] = str(token_balance)
            base_payload["allowance_wei"] = str(allowance)
            base_payload["approval_required"] = allowance < bond_wei
            if native_balance == 0:
                issues.append("Signer wallet has zero native gas balance.")
            if token_balance < bond_wei:
                issues.append("Signer wallet does not hold enough collateral token balance for the configured bond.")
            if allowance < bond_wei:
                issues.append("ERC-20 allowance is below the configured bond. Approve the OO contract before going live.")

            calldata = _build_erc20_approve_calldata(oo_address, bond_wei)
            gas_price_hex = await rpc.request("eth_gasPrice", [])
            gas_estimate_hex = await rpc.request(
                "eth_estimateGas",
                [
                    {
                        "from": signer_address,
                        "to": currency_address,
                        "data": calldata,
                    }
                ],
            )
            gas_price = _coerce_int(gas_price_hex, field_name="eth_gasPrice")
            gas_estimate = _coerce_int(gas_estimate_hex, field_name="eth_estimateGas")
            base_payload["tx_preview"] = {
                "method": "approve(address,uint256)",
                "spender_address": oo_address,
                "amount_wei": str(bond_wei),
                "gas_price_wei": str(gas_price),
                "gas_limit": gas_estimate + 25_000,
                "data": calldata,
            }

        base_payload["issues"] = issues
        base_payload["ready_for_live_submission"] = len(issues) == 0
        return base_payload

    async def approve_bond_allowance(self, amount_wei: str | None = None) -> dict[str, object]:
        target_amount = _coerce_int(amount_wei or settings.oracle_bond_wei, field_name="amount_wei")
        if settings.oracle_execution_mode != "live":
            return {
                "provider": "uma_optimistic_oracle_v3",
                "execution_mode": settings.oracle_execution_mode,
                "status": "simulated",
                "chain_id": settings.oracle_chain_id,
                "signer_address": settings.oracle_signer_address or None,
                "spender_address": settings.oracle_uma_oo_address or None,
                "currency_address": settings.oracle_currency_address or None,
                "amount_wei": str(target_amount),
                "allowance_before_wei": "0",
                "tx_hash": None,
                "submission_status": "simulated",
                "nonce": None,
                "gas_limit": None,
                "gas_price_wei": None,
            }

        signer_address, private_key = self._resolve_live_signer()
        oo_address = _normalize_address(settings.oracle_uma_oo_address, field_name="ORACLE_UMA_OO_ADDRESS")
        currency_address = _normalize_address(settings.oracle_currency_address, field_name="ORACLE_CURRENCY_ADDRESS")
        rpc, rpc_chain_id = await self._build_live_rpc_context()
        allowance_before = await self._read_uint256(
            rpc,
            contract_address=currency_address,
            signature="allowance(address,address)",
            argument_types=["address", "address"],
            args=[signer_address, oo_address],
        )
        if allowance_before >= target_amount:
            return {
                "provider": "uma_optimistic_oracle_v3",
                "execution_mode": settings.oracle_execution_mode,
                "status": "already_approved",
                "chain_id": rpc_chain_id,
                "signer_address": signer_address,
                "spender_address": oo_address,
                "currency_address": currency_address,
                "amount_wei": str(target_amount),
                "allowance_before_wei": str(allowance_before),
                "tx_hash": None,
                "submission_status": "already_approved",
                "nonce": None,
                "gas_limit": None,
                "gas_price_wei": None,
            }

        calldata = _build_erc20_approve_calldata(oo_address, target_amount)
        nonce_hex = await rpc.request("eth_getTransactionCount", [signer_address, "pending"])
        gas_price_hex = await rpc.request("eth_gasPrice", [])
        gas_limit_hex = await rpc.request(
            "eth_estimateGas",
            [
                {
                    "from": signer_address,
                    "to": currency_address,
                    "data": calldata,
                }
            ],
        )
        nonce = _coerce_int(nonce_hex, field_name="eth_getTransactionCount")
        gas_price = _coerce_int(gas_price_hex, field_name="eth_gasPrice")
        gas_limit = _coerce_int(gas_limit_hex, field_name="eth_estimateGas") + 25_000
        tx = {
            "chainId": rpc_chain_id,
            "nonce": nonce,
            "gas": gas_limit,
            "gasPrice": gas_price,
            "to": currency_address,
            "value": 0,
            "data": calldata,
        }
        signed = Account.sign_transaction(tx, private_key)
        tx_hash_result = await rpc.request("eth_sendRawTransaction", [signed.raw_transaction.hex()])
        if not isinstance(tx_hash_result, str):
            raise OracleConfigurationError("ERC-20 approval did not return a transaction hash.")
        return {
            "provider": "uma_optimistic_oracle_v3",
            "execution_mode": settings.oracle_execution_mode,
            "status": "submitted",
            "chain_id": rpc_chain_id,
            "signer_address": signer_address,
            "spender_address": oo_address,
            "currency_address": currency_address,
            "amount_wei": str(target_amount),
            "allowance_before_wei": str(allowance_before),
            "tx_hash": tx_hash_result,
            "submission_status": "submitted",
            "nonce": nonce,
            "gas_limit": gas_limit,
            "gas_price_wei": str(gas_price),
        }

    async def begin_resolution(self, request: OracleResolutionRequest) -> dict[str, object]:
        assertion_hash = sha256(f"{request.market_slug}:{request.candidate_id}".encode("utf-8")).hexdigest()
        simulated_assertion_id = f"uma-dev-{assertion_hash[:24]}"
        payload = self._build_assertion_payload(request, signer_address=settings.oracle_signer_address or None)
        payload["assertion_id"] = simulated_assertion_id
        if settings.oracle_execution_mode != "live":
            payload["submission_status"] = "simulated"
            return payload

        signer_address, private_key = self._resolve_live_signer()
        oo_address = _normalize_address(settings.oracle_uma_oo_address, field_name="ORACLE_UMA_OO_ADDRESS")
        currency_address = _normalize_address(settings.oracle_currency_address, field_name="ORACLE_CURRENCY_ADDRESS")
        escalation_manager = _normalize_address(
            settings.oracle_uma_escalation_manager,
            field_name="ORACLE_UMA_ESCALATION_MANAGER",
            allow_zero=True,
        )
        liveness_seconds = settings.oracle_liveness_minutes * 60
        bond_wei = _coerce_int(settings.oracle_bond_wei, field_name="ORACLE_BOND_WEI")
        reward_wei = _coerce_int(settings.oracle_reward_wei, field_name="ORACLE_REWARD_WEI")
        rpc, rpc_chain_id = await self._build_live_rpc_context()
        calldata = _build_assert_truth_calldata(
            claim=_build_uma_claim(request),
            asserter=signer_address,
            callback_recipient=ZERO_ADDRESS,
            escalation_manager=escalation_manager,
            liveness_seconds=liveness_seconds,
            currency=currency_address,
            bond_wei=bond_wei,
            identifier=settings.oracle_uma_assertion_identifier,
            domain_id=ZERO_BYTES32,
        )

        preflight_result = await rpc.request(
            "eth_call",
            [
                {
                    "from": signer_address,
                    "to": oo_address,
                    "data": calldata,
                },
                "latest",
            ],
        )
        if not isinstance(preflight_result, str):
            raise OracleConfigurationError("UMA live preflight did not return an assertion identifier.")
        assertion_id = _decode_assertion_id(preflight_result)
        nonce_hex = await rpc.request("eth_getTransactionCount", [signer_address, "pending"])
        gas_price_hex = await rpc.request("eth_gasPrice", [])
        gas_limit_hex = await rpc.request(
            "eth_estimateGas",
            [
                {
                    "from": signer_address,
                    "to": oo_address,
                    "data": calldata,
                }
            ],
        )
        nonce = _coerce_int(nonce_hex, field_name="eth_getTransactionCount")
        gas_price = _coerce_int(gas_price_hex, field_name="eth_gasPrice")
        estimated_gas = _coerce_int(gas_limit_hex, field_name="eth_estimateGas")
        gas_limit = max(estimated_gas + 50_000, estimated_gas)

        tx = {
            "chainId": rpc_chain_id,
            "nonce": nonce,
            "gas": gas_limit,
            "gasPrice": gas_price,
            "to": oo_address,
            "value": 0,
            "data": calldata,
        }
        signed = Account.sign_transaction(tx, private_key)
        raw_tx = signed.raw_transaction.hex()
        tx_hash_result = await rpc.request("eth_sendRawTransaction", [raw_tx])
        if not isinstance(tx_hash_result, str):
            raise OracleConfigurationError("UMA live submission did not return a transaction hash.")
        payload.update(
            {
                "assertion_id": assertion_id,
                "signer_address": signer_address,
                "submission_status": "submitted",
                "rpc_chain_id": rpc_chain_id,
                "signer_key_hint": _mask_private_value(settings.oracle_signer_private_key),
                "tx_hash": tx_hash_result,
                "nonce": nonce,
                "gas_limit": gas_limit,
                "gas_price_wei": str(gas_price),
                "prepared_call": {
                    "method": "assertTruth",
                    "contract_address": oo_address,
                    "identifier": settings.oracle_uma_assertion_identifier,
                    "currency": currency_address,
                    "bond_wei": str(bond_wei),
                    "reward_wei": str(reward_wei),
                    "liveness_seconds": liveness_seconds,
                    "callback_recipient": ZERO_ADDRESS,
                    "escalation_manager": escalation_manager,
                    "data": calldata,
                },
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "last_reconciled_at": None,
            }
        )
        return payload

    async def reconcile_resolution(self, request: OracleResolutionStatusRequest) -> dict[str, object]:
        payload = dict(request.current_payload)
        payload.setdefault("provider", "uma_optimistic_oracle_v3")
        if settings.oracle_execution_mode != "live":
            payload.setdefault("submission_status", "simulated")
            payload["last_reconciled_at"] = datetime.now(timezone.utc).isoformat()
            return payload

        rpc, _ = await self._build_live_rpc_context()
        payload["last_reconciled_at"] = datetime.now(timezone.utc).isoformat()

        tx_hash = payload.get("tx_hash")
        if not isinstance(tx_hash, str) or not tx_hash.strip():
            payload.setdefault("submission_status", "not_submitted")
            return payload

        receipt_result = await rpc.request("eth_getTransactionReceipt", [tx_hash])
        if receipt_result is None:
            payload["submission_status"] = "submitted"
            payload["receipt_status"] = "pending"
            return payload
        if not isinstance(receipt_result, dict):
            raise OracleConfigurationError("UMA receipt lookup returned an unexpected payload.")

        receipt_status = _coerce_int(receipt_result.get("status"), field_name="receipt.status")
        payload["receipt_status"] = "confirmed" if receipt_status == 1 else "failed"
        payload["submission_status"] = "confirmed" if receipt_status == 1 else "failed"
        block_number = receipt_result.get("blockNumber")
        gas_used = receipt_result.get("gasUsed")
        transaction_index = receipt_result.get("transactionIndex")
        if block_number is not None:
            payload["receipt_block_number"] = _coerce_int(block_number, field_name="receipt.blockNumber")
        if gas_used is not None:
            payload["receipt_gas_used"] = str(_coerce_int(gas_used, field_name="receipt.gasUsed"))
        if transaction_index is not None:
            payload["receipt_transaction_index"] = _coerce_int(
                transaction_index,
                field_name="receipt.transactionIndex",
            )

        receipt_assertion_id = _extract_assertion_id_from_receipt(receipt_result)
        if receipt_assertion_id:
            payload["assertion_id"] = receipt_assertion_id

        assertion_id = payload.get("assertion_id")
        oo_address = payload.get("oracle_contract_address") or settings.oracle_uma_oo_address
        if receipt_status != 1 or not isinstance(assertion_id, str) or not assertion_id.strip() or not oo_address:
            return payload

        assertion_result = await rpc.request(
            "eth_call",
            [
                {
                    "to": _normalize_address(str(oo_address), field_name="ORACLE_UMA_OO_ADDRESS"),
                    "data": _build_get_assertion_calldata(assertion_id),
                },
                "latest",
            ],
        )
        if not isinstance(assertion_result, str):
            raise OracleConfigurationError("UMA getAssertion returned an unexpected payload.")
        payload.update(_decode_assertion_state(assertion_result))
        return payload
