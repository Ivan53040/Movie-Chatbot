export default function PromptChips({ prompts, onPromptClick }) {
  return (
    <section className="prompt-row" aria-label="Suggested prompts">
      {prompts.map((prompt) => (
        <button className="prompt-chip" type="button" key={prompt} onClick={() => onPromptClick(prompt)}>
          {prompt}
        </button>
      ))}
    </section>
  );
}
