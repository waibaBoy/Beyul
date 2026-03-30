"use client";

import { useState } from "react";

type SuccessMessage<T> = string | ((result: T) => string);

type UseAuthActionResult = {
  errorMessage: string;
  isSubmitting: boolean;
  statusMessage: string;
  runAction: <T>(
    message: string,
    action: () => Promise<T>,
    options?: {
      successMessage?: SuccessMessage<T>;
    }
  ) => Promise<T | undefined>;
  setStatusMessage: (message: string) => void;
};

export const useAuthAction = (initialMessage: string): UseAuthActionResult => {
  const [statusMessage, setStatusMessage] = useState(initialMessage);
  const [errorMessage, setErrorMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const runAction = async <T>(
    message: string,
    action: () => Promise<T>,
    options?: {
      successMessage?: SuccessMessage<T>;
    }
  ): Promise<T | undefined> => {
    setErrorMessage("");
    setStatusMessage(message);
    setIsSubmitting(true);

    try {
      const result = await action();
      const successMessage = options?.successMessage;
      if (typeof successMessage === "function") {
        setStatusMessage(successMessage(result));
      } else if (typeof successMessage === "string") {
        setStatusMessage(successMessage);
      }
      return result;
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unexpected auth error");
    } finally {
      setIsSubmitting(false);
    }
  };

  return {
    errorMessage,
    isSubmitting,
    statusMessage,
    runAction,
    setStatusMessage
  };
};
