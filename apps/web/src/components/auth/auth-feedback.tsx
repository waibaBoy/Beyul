type AuthFeedbackProps = {
  errorMessage: string;
  statusMessage: string;
};

export const AuthFeedback = ({ errorMessage, statusMessage }: AuthFeedbackProps) => {
  return <div className={`auth-feedback ${errorMessage ? "error" : ""}`}>{errorMessage || statusMessage}</div>;
};
