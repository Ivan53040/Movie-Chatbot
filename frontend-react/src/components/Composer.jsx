export default function Composer({ value, isLoading, onChange, onSubmit }) {
  function handleKeyDown(event) {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) {
      return;
    }
    event.preventDefault();
    onSubmit(event);
  }

  return (
    <form className="composer" onSubmit={onSubmit}>
      <label className="composer-label" htmlFor="message-input">
        Message
      </label>
      <div className="composer-frame">
        <input
          id="message-input"
          name="message"
          className="composer-input"
          type="text"
          placeholder="Describe what you want to watch..."
          autoComplete="off"
          value={value}
          disabled={isLoading}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button className="send-button" type="submit" disabled={isLoading}>
          {isLoading ? "Thinking..." : "Send"}
        </button>
      </div>
      <div className="composer-footer">
        <span>Examples: "funny but not childish", "like Inception", "sad romance"</span>
      </div>
    </form>
  );
}
