export default function TypingMessage() {
  return (
    <article className="message message-bot typing-message">
      <div className="sender-row">
        <div className="bot-avatar">MB</div>
        <div className="message-meta">MovieBot</div>
      </div>
      <div className="bubble bubble-bot bubble-typing">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </article>
  );
}
