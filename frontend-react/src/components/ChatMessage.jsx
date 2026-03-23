import { useEffect, useState } from "react";

export default function ChatMessage({
  message,
  onOptionSelect,
  onFeedbackSelect,
  onFeedbackReasonSubmit,
}) {
  const [expandedIndex, setExpandedIndex] = useState(0);
  const [reasonText, setReasonText] = useState("");
  const [displayText, setDisplayText] = useState(message.role === "assistant" ? "" : message.text || "");
  const [isTextComplete, setIsTextComplete] = useState(message.role !== "assistant");

  useEffect(() => {
    if (message.feedback?.status === "awaiting_reason") {
      setReasonText(message.feedback?.reasonDraft || "");
      return;
    }
    if (message.feedback?.status === "reason_saved") {
      setReasonText("");
    }
  }, [message.feedback?.reasonDraft, message.feedback?.status]);

  useEffect(() => {
    if (message.role !== "assistant") {
      setDisplayText(message.text || "");
      setIsTextComplete(true);
      return;
    }

    const fullText = String(message.text || "");
    if (!fullText) {
      setDisplayText("");
      setIsTextComplete(true);
      return;
    }

    if (message.animateText === false) {
      setDisplayText(fullText);
      setIsTextComplete(true);
      return;
    }

    setDisplayText("");
    setIsTextComplete(false);
    let index = 0;
    const intervalId = window.setInterval(() => {
      index += 1;
      setDisplayText(fullText.slice(0, index));
      if (index >= fullText.length) {
        window.clearInterval(intervalId);
        setIsTextComplete(true);
      }
    }, Math.max(10, Math.min(22, 420 / fullText.length)));

    return () => window.clearInterval(intervalId);
  }, [message.animateText, message.id, message.role, message.text]);

  if (message.role === "user") {
    return (
      <article className="message message-user">
        <div className="message-meta">You</div>
        <div className="bubble bubble-user">{message.text}</div>
      </article>
    );
  }

  return (
    <article className="message message-bot">
      <div className="sender-row">
        <div className="bot-avatar">MB</div>
        <div className="message-meta">MovieBot</div>
      </div>
      <div className="bubble bubble-bot">
        {displayText}
        {!isTextComplete ? <span className="message-cursor" aria-hidden="true" /> : null}
      </div>

      {isTextComplete && message.emptyState ? (
        <section className="empty-state-card">
          <p className="empty-state-label">Suggestion</p>
          <p className="empty-state-hint">{message.emptyState.hint}</p>
        </section>
      ) : null}

      {isTextComplete && message.options?.length ? (
        <section className="clarification-options" aria-label="Clarification options">
          {message.options.map((option) => (
            <button
              className="clarification-option"
              key={`${message.id}-${option.id}-${option.name || option.label}`}
              type="button"
              onClick={() => onOptionSelect?.(option, message)}
            >
              {option.label}
            </button>
          ))}
        </section>
      ) : null}

      {isTextComplete && message.picks?.length ? (
        <section className="recommendation-stack">
          {message.picks.map((pick, index) => {
            const isExpanded = index === expandedIndex;
            const cardClassName = [
              "movie-card",
              isExpanded ? "movie-card-expanded" : "movie-card-collapsed",
              isExpanded ? "movie-card-featured" : "",
            ]
              .filter(Boolean)
              .join(" ");

            return (
              <button
                className={cardClassName}
                key={`${message.id}-${pick.title}`}
                type="button"
                onClick={() => setExpandedIndex((current) => (current === index ? -1 : index))}
              >
                <div className="movie-card-header">
                  <div className="movie-card-header-copy">
                    {index === 0 ? <p className="movie-kicker">Top pick</p> : null}
                    <h2>{pick.title}</h2>
                    {pick.meta ? <p className="movie-meta">{pick.meta}</p> : null}
                  </div>
                  <span className="movie-card-toggle">
                    {isExpanded ? "Hide" : "Open"}
                  </span>
                </div>
                <div className={`movie-description-wrap ${isExpanded ? "movie-description-wrap-expanded" : ""}`}>
                  {pick.description ? <p className="movie-description">{pick.description}</p> : null}
                </div>
              </button>
            );
          })}
        </section>
      ) : null}

      {isTextComplete && message.feedback ? (
        <section className="feedback-card">
          <p className="feedback-prompt">{message.feedback.prompt}</p>
          {message.feedback.status === "idle" ? (
            <div className="feedback-actions">
              <button
                className="feedback-button"
                type="button"
                onClick={() => onFeedbackSelect?.(message, true)}
              >
                {message.feedback.yesLabel}
              </button>
              <button
                className="feedback-button feedback-button-secondary"
                type="button"
                onClick={() => onFeedbackSelect?.(message, false)}
              >
                {message.feedback.noLabel}
              </button>
            </div>
          ) : null}
          {message.feedback.status === "submitting" ? (
            <p className="feedback-note">{message.feedback.loadingText}</p>
          ) : null}
          {message.feedback.status === "positive" ? (
            <p className="feedback-note">{message.feedback.positiveText}</p>
          ) : null}
          {message.feedback.status === "awaiting_reason" ? (
            <form
              className="feedback-reason-form"
              onSubmit={(event) => {
                event.preventDefault();
                onFeedbackReasonSubmit?.(message, reasonText);
              }}
            >
              <p className="feedback-note">
                {message.feedback.reasonPrompt ||
                  "Could you tell me why these results did not help?"}
              </p>
              <textarea
                className="feedback-reason-input"
                rows={3}
                value={reasonText}
                onChange={(event) => setReasonText(event.target.value)}
                placeholder={
                  message.feedback.reasonPlaceholder ||
                  "For example: too old, wrong franchise, not the mood I wanted."
                }
              />
              {message.feedback.reasonError ? (
                <p className="feedback-error">{message.feedback.reasonError}</p>
              ) : null}
              <div className="feedback-reason-actions">
                <button
                  className="feedback-button"
                  type="submit"
                  disabled={!reasonText.trim()}
                >
                  {message.feedback.reasonSubmitLabel || "Send"}
                </button>
              </div>
            </form>
          ) : null}
          {message.feedback.status === "saving_reason" ? (
            <p className="feedback-note">
              {message.feedback.reasonSavingText || "Saving your note..."}
            </p>
          ) : null}
          {message.feedback.status === "reason_saved" ? (
            <p className="feedback-note">
              {message.feedback.reasonSavedText || "Got it. I logged your reason as well."}
            </p>
          ) : null}
          {message.feedback.status === "negative" && message.feedback.negativeText ? (
            <p className="feedback-note">{message.feedback.negativeText}</p>
          ) : null}
        </section>
      ) : null}
    </article>
  );
}
