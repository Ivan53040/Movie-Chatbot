const messages = document.querySelector("#messages");
const composer = document.querySelector("#composer");
const input = document.querySelector("#message-input");

document.querySelectorAll(".prompt-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    input.value = chip.textContent.trim();
    input.focus();
  });
});

composer.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) {
    return;
  }

  appendUserMessage(text);
  input.value = "";

  const typingNode = appendTyping();

  try {
    const response = await fetchChatResponse(text);
    typingNode.remove();
    appendBotMessage(response);
  } catch (error) {
    typingNode.remove();
    appendBotMessage({
      intro: error.message || "Something went wrong while fetching recommendations.",
      picks: [],
    });
  }
});

async function fetchChatResponse(text) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: text,
      top_k: 3,
    }),
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Request failed.");
  }

  return {
    intro: payload.reply_text || "Here are a few matches.",
    language: payload.ui_language || "en",
    route: payload.route || "",
    parsedQuery: payload.parsed_query || {},
    picks: (payload.results || []).slice(0, 3).map((movie, index) => ({
      title: movie.title || "Untitled",
      meta: buildMeta(movie),
      description: index === 0 ? buildDescription(movie) : "",
      featured: index === 0,
    })),
  };
}

function buildMeta(movie) {
  const parts = [];
  if (movie.year) {
    parts.push(String(movie.year));
  }

  const genres = movie.genres || movie.genre || [];
  const genreList = Array.isArray(genres) ? genres : [genres];
  const compactGenres = genreList
    .map((item) => String(item).trim())
    .filter(Boolean)
    .slice(0, 2);

  if (compactGenres.length) {
    parts.push(compactGenres.join(" / "));
  }

  return parts.join(" / ");
}

function buildDescription(movie) {
  if (movie.top_pick_text) {
    return movie.top_pick_text;
  }

  if (movie.overview) {
    return movie.overview;
  }

  return "This is currently the strongest match from the recommendation pipeline.";
}

function appendUserMessage(text) {
  const template = document.querySelector("#user-message-template");
  const node = template.content.firstElementChild.cloneNode(true);
  node.querySelector(".bubble").textContent = text;
  messages.appendChild(node);
  scrollToBottom();
}

function appendTyping() {
  const template = document.querySelector("#typing-template");
  const node = template.content.firstElementChild.cloneNode(true);
  messages.appendChild(node);
  scrollToBottom();
  return node;
}

function appendBotMessage(response) {
  const template = document.querySelector("#bot-message-template");
  const node = template.content.firstElementChild.cloneNode(true);
  node.querySelector(".bot-text").textContent = response.intro;
  const isChinese = response.language === "zh";

  const insights = node.querySelector(".message-insights");
  const routePill = node.querySelector(".route-pill");
  const queryChipRow = node.querySelector(".query-chip-row");

  if (response.route) {
    routePill.textContent = isChinese
      ? `路由：${response.route}`
      : `Route: ${response.route}`;
  } else {
    routePill.remove();
  }

  const parsedEntries = Object.entries(response.parsedQuery || {}).filter(([, value]) => {
    if (value === null || value === undefined) {
      return false;
    }
    if (typeof value === "string") {
      return value.trim().length > 0;
    }
    return true;
  });

  parsedEntries.forEach(([key, value]) => {
    const chip = document.createElement("span");
    chip.className = "query-chip";
    chip.textContent = `${key}: ${formatParsedValue(value)}`;
    queryChipRow.appendChild(chip);
  });

  if (!response.route && !parsedEntries.length) {
    insights.remove();
  }

  const stack = node.querySelector(".recommendation-stack");
  response.picks.forEach((pick) => {
    const card = document.createElement("article");
    card.className = pick.featured ? "movie-card movie-card-featured" : "movie-card";

    if (pick.featured) {
      const kicker = document.createElement("p");
      kicker.className = "movie-kicker";
      kicker.textContent = isChinese ? "首選" : "Top pick";
      card.appendChild(kicker);
    }

    const title = document.createElement("h2");
    title.textContent = pick.title;
    card.appendChild(title);

    if (pick.meta) {
      const meta = document.createElement("p");
      meta.className = "movie-meta";
      meta.textContent = pick.meta;
      card.appendChild(meta);
    }

    if (pick.description) {
      const description = document.createElement("p");
      description.className = "movie-description";
      description.textContent = pick.description;
      card.appendChild(description);
    }

    stack.appendChild(card);
  });

  if (!response.picks.length) {
    stack.remove();
  }

  messages.appendChild(node);
  scrollToBottom();
}

function scrollToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function formatParsedValue(value) {
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  return String(value);
}
