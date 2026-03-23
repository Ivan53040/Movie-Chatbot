import { useEffect, useRef } from "react";
import ChatMessage from "./ChatMessage";
import TypingMessage from "./TypingMessage";

export default function MessageList({
  messages,
  isLoading,
  onOptionSelect,
  onFeedbackSelect,
  onFeedbackReasonSubmit,
}) {
  const containerRef = useRef(null);

  useEffect(() => {
    const node = containerRef.current;
    if (!node) {
      return;
    }
    node.scrollTop = node.scrollHeight;
  }, [messages, isLoading]);

  return (
    <section className="messages" id="messages" aria-live="polite" ref={containerRef}>
      {messages.map((message) => (
        <ChatMessage
          key={message.id}
          message={message}
          onOptionSelect={onOptionSelect}
          onFeedbackSelect={onFeedbackSelect}
          onFeedbackReasonSubmit={onFeedbackReasonSubmit}
        />
      ))}
      {isLoading ? <TypingMessage /> : null}
    </section>
  );
}
