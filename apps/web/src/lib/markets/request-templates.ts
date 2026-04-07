import type { MarketTemplateConfig, MarketTemplateKey } from "@/lib/api/types";
import { normalizeSlug } from "@/lib/slug";

export type TemplateBuilderInput = {
  templateKey: MarketTemplateKey;
  subject: string;
  referenceAsset: string;
  thresholdValue: string;
  timeframeLabel: string;
  intervalLabel: string;
  category: string;
  subcategory: string;
  referenceSourceLabel: string;
  referencePrice: string;
  referenceTimestamp: string;
  contractNotes: string;
};

export type MarketTemplateDefinition = {
  key: MarketTemplateKey;
  label: string;
  description: string;
  defaultCategory: string;
  needsThreshold: boolean;
  needsInterval: boolean;
  buildDraft: (input: TemplateBuilderInput) => {
    title: string;
    question: string;
    description: string;
    slug: string;
    templateConfig: MarketTemplateConfig;
  };
};

export type TemplateValidationResult = {
  fieldErrors: Partial<Record<keyof TemplateBuilderInput, string>>;
};

const buildTemplateConfig = (input: TemplateBuilderInput): MarketTemplateConfig => ({
  category: input.category || undefined,
  subcategory: input.subcategory || undefined,
  subject: input.subject || undefined,
  reference_asset: input.referenceAsset || undefined,
  threshold_value: input.thresholdValue || undefined,
  timeframe_label: input.timeframeLabel || undefined,
  interval_label: input.intervalLabel || undefined,
  reference_source_label: input.referenceSourceLabel || undefined,
  reference_price: input.referencePrice || undefined,
  reference_timestamp: input.referenceTimestamp || undefined,
  reference_label: input.referenceAsset
    ? `${input.referenceAsset} ${input.referenceSourceLabel ? input.referenceSourceLabel.toLowerCase() : "price"}`
    : undefined,
  contract_notes: input.contractNotes || undefined
});

export const marketTemplateDefinitions: MarketTemplateDefinition[] = [
  {
    key: "price_above",
    label: "Price above",
    description: "Binary market that resolves Yes if the asset closes above a target value.",
    defaultCategory: "Crypto",
    needsThreshold: true,
    needsInterval: false,
    buildDraft: (input) => {
      const threshold = input.thresholdValue || "the target";
      const timeframe = input.timeframeLabel || "the selected period";
      const subject = input.subject || input.referenceAsset || "the asset";
      return {
        title: `Will ${subject} close above ${threshold}?`,
        question: `Will ${subject} close above ${threshold} ${timeframe}?`,
        description: `This market resolves Yes if ${subject} closes above ${threshold} ${timeframe}.`,
        slug: normalizeSlug(`${subject}-above-${threshold}`),
        templateConfig: buildTemplateConfig(input)
      };
    }
  },
  {
    key: "price_below",
    label: "Price below",
    description: "Binary market that resolves Yes if the asset closes below a target value.",
    defaultCategory: "Crypto",
    needsThreshold: true,
    needsInterval: false,
    buildDraft: (input) => {
      const threshold = input.thresholdValue || "the target";
      const timeframe = input.timeframeLabel || "the selected period";
      const subject = input.subject || input.referenceAsset || "the asset";
      return {
        title: `Will ${subject} close below ${threshold}?`,
        question: `Will ${subject} close below ${threshold} ${timeframe}?`,
        description: `This market resolves Yes if ${subject} closes below ${threshold} ${timeframe}.`,
        slug: normalizeSlug(`${subject}-below-${threshold}`),
        templateConfig: buildTemplateConfig(input)
      };
    }
  },
  {
    key: "up_down_interval",
    label: "Up or down interval",
    description: "Resolves Yes if the asset is up over a short interval.",
    defaultCategory: "Crypto",
    needsThreshold: false,
    needsInterval: true,
    buildDraft: (input) => {
      const interval = input.intervalLabel || "the interval";
      const subject = input.subject || input.referenceAsset || "the asset";
      return {
        title: `${subject} up or down - ${interval}`,
        question: `Will ${subject} be up over ${interval}?`,
        description: `This market resolves Yes if ${subject} ends the ${interval} above the opening reference price.`,
        slug: normalizeSlug(`${subject}-up-down-${interval}`),
        templateConfig: buildTemplateConfig(input)
      };
    }
  },
  {
    key: "event_outcome",
    label: "Event outcome",
    description: "Binary market for elections, sports, policy decisions, and other named events.",
    defaultCategory: "Politics",
    needsThreshold: false,
    needsInterval: false,
    buildDraft: (input) => {
      const timeframe = input.timeframeLabel || "the event window";
      const subject = input.subject || "the event";
      return {
        title: `Will ${subject} happen?`,
        question: `Will ${subject} happen during ${timeframe}?`,
        description: `This market resolves Yes if the named event occurs during ${timeframe}.`,
        slug: normalizeSlug(subject),
        templateConfig: buildTemplateConfig(input)
      };
    }
  }
];

export const marketTemplateDefinitionByKey = Object.fromEntries(
  marketTemplateDefinitions.map((template) => [template.key, template])
) as Record<MarketTemplateKey, MarketTemplateDefinition>;

export const getTemplateDraft = (input: TemplateBuilderInput) =>
  marketTemplateDefinitionByKey[input.templateKey].buildDraft(input);

export const buildTemplateContractPrefill = (
  templateKey: string | null | undefined,
  templateConfig: MarketTemplateConfig | null | undefined
) => {
  if (!templateKey || !templateConfig) {
    return {};
  }

  if (templateKey === "price_above" || templateKey === "price_below") {
    return {
      category: templateConfig.category ?? "",
      subcategory: templateConfig.subcategory ?? templateConfig.subject ?? "",
      reference_label:
        templateConfig.reference_label ??
        (templateConfig.reference_asset ? `${templateConfig.reference_asset} price` : ""),
      reference_source_label: templateConfig.reference_source_label ?? "",
      reference_asset: templateConfig.reference_asset ?? "",
      reference_price: templateConfig.reference_price ?? "",
      price_to_beat: templateConfig.threshold_value ?? "",
      reference_timestamp: templateConfig.reference_timestamp ?? "",
      contract_notes: templateConfig.contract_notes ?? ""
    };
  }

  if (templateKey === "up_down_interval") {
    return {
      category: templateConfig.category ?? "",
      subcategory: templateConfig.subcategory ?? templateConfig.subject ?? "",
      reference_label:
        templateConfig.reference_label ??
        (templateConfig.reference_asset ? `${templateConfig.reference_asset} price` : ""),
      reference_source_label: templateConfig.reference_source_label ?? "",
      reference_asset: templateConfig.reference_asset ?? "",
      reference_price: templateConfig.reference_price ?? "",
      price_to_beat: templateConfig.reference_price ?? "",
      reference_timestamp: templateConfig.reference_timestamp ?? "",
      contract_notes: templateConfig.contract_notes ?? ""
    };
  }

  if (templateKey === "event_outcome") {
    return {
      category: templateConfig.category ?? "",
      subcategory: templateConfig.subcategory ?? templateConfig.subject ?? "",
      reference_label: templateConfig.reference_label ?? templateConfig.reference_source_label ?? "",
      reference_source_label: templateConfig.reference_source_label ?? "",
      reference_asset: templateConfig.reference_asset ?? "",
      reference_price: templateConfig.reference_price ?? "",
      price_to_beat: "",
      reference_timestamp: templateConfig.reference_timestamp ?? "",
      contract_notes: templateConfig.contract_notes ?? ""
    };
  }

  return {};
};

export const validateTemplateBuilder = (input: TemplateBuilderInput): TemplateValidationResult => {
  const fieldErrors: TemplateValidationResult["fieldErrors"] = {};

  if (!input.subject.trim()) {
    fieldErrors.subject = "Subject is required.";
  }
  if (!input.category.trim()) {
    fieldErrors.category = "Category is required.";
  }

  if (["price_above", "price_below", "up_down_interval"].includes(input.templateKey) && !input.referenceAsset.trim()) {
    fieldErrors.referenceAsset = "Reference asset is required for price-based templates.";
  }

  if (["price_above", "price_below"].includes(input.templateKey) && !input.thresholdValue.trim()) {
    fieldErrors.thresholdValue = "Target value is required for threshold markets.";
  }

  if (input.templateKey === "up_down_interval" && !input.intervalLabel.trim()) {
    fieldErrors.intervalLabel = "Interval label is required for interval markets.";
  }

  if (input.referencePrice.trim() && Number.isNaN(Number(input.referencePrice))) {
    fieldErrors.referencePrice = "Reference price must be numeric.";
  }

  if (input.thresholdValue.trim() && Number.isNaN(Number(input.thresholdValue))) {
    fieldErrors.thresholdValue = "Target value must be numeric.";
  }

  if (input.referenceTimestamp.trim() && Number.isNaN(Date.parse(input.referenceTimestamp))) {
    fieldErrors.referenceTimestamp = "Reference timestamp must be a valid ISO datetime.";
  }

  return { fieldErrors };
};
