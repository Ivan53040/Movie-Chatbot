import { useState } from "react";
import Composer from "./components/Composer";
import MessageList from "./components/MessageList";
import PromptChips from "./components/PromptChips";

const PROMPT_LIBRARY = [
  "Something like Interstellar",
  "Funny movie tonight",
  "Korean thriller",
  "Romance after 2015",
  "Mind-bending sci-fi",
  "A sad movie that is still beautiful",
  "Light comedy for a lazy night",
  "A thriller with a great twist",
  "Space movie with emotion",
  "Something like Inception",
  "Animated movie for adults",
  "Warm family movie",
  "Dark detective story",
  "A24-style emotional drama",
  "Something like Parasite",
  "Slow-burn mystery",
  "Cozy romance movie",
  "Action movie with strong story",
  "Japanese animated fantasy",
  "A movie about time travel",
  "Something visually stunning",
  "Movie with a clever ending",
  "Underrated sci-fi",
  "Feel-good movie tonight",
  "Crime movie based on true events",
  "Something like La La Land",
  "Nostalgic coming-of-age movie",
  "Tense survival story",
  "A really emotional romance",
  "Funny but not childish",
  "Something like The Dark Knight",
  "Movie with aliens",
  "A quiet introspective film",
  "Courtroom drama",
  "Heist movie with style",
  "Something like Whiplash",
  "Fantasy adventure with heart",
  "Smart political thriller",
  "Movie set in space",
  "A wholesome animated movie",
  "Korean revenge movie",
  "Romantic movie for date night",
  "Movie with philosophical themes",
  "A great Christopher Nolan movie",
  "Something intense and suspenseful",
  "Feel-good sports movie",
  "A movie about memory and identity",
  "Rainy day movie",
  "Something like Her",
  "Beautifully shot drama",
];

const WELCOME_MESSAGES = [
  "Hi, I am MovieBot. Tell me what kind of movie you want to watch, and I will suggest a few good matches.",
  "Hello. Give me a genre, a mood, or a movie you like, and I will find something close to it.",
  "What do you feel like watching tonight? I can suggest a few movies based on vibe, genre, or a favorite title.",
  "Tell me a movie you loved, and I will recommend a few similar picks.",
  "If you want, start with something simple like funny, dark, emotional, or sci-fi, and I will take it from there.",
  "Describe the kind of movie you are in the mood for, and I will give you a short list to start with.",
  "Need a movie idea? Tell me a feeling, a theme, or an example movie, and I will suggest a few matches.",
  "You can ask for something like Interstellar, a funny movie tonight, or a romance after 2015. I will handle the rest.",
  "Tell me what you want to watch, and I will recommend a few options with the strongest pick highlighted first.",
  "Start with any movie vibe you want, and I will turn it into a few recommendation picks."
];

export default function App() {
  const [messages, setMessages] = useState(() => [buildWelcomeMessage()]);
  const [prompts] = useState(() => pickRandomItems(PROMPT_LIBRARY, 4));
  const [sessionId] = useState(() => getOrCreateSessionId());
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [lastRecommendationRequest, setLastRecommendationRequest] = useState(null);
  const [pendingClarification, setPendingClarification] = useState(null);
  const [pendingFeedbackReason, setPendingFeedbackReason] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    const text = inputValue.trim();
    if (!text || isLoading) {
      return;
    }

    const userMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      text,
    };

    setMessages((current) => [...current, userMessage]);
    setInputValue("");
    setIsLoading(true);

    try {
      if (pendingClarification) {
        const followUpMessage = await handleClarificationInput(
          text,
          pendingClarification,
          sessionId
        );
        setMessages((current) => [...current, followUpMessage]);
        if (followUpMessage.resolvedClarification) {
          setPendingClarification(null);
        }
        if (followUpMessage.nextRecommendationRequest) {
          setLastRecommendationRequest(followUpMessage.nextRecommendationRequest);
        }
        return;
      }

      if (false && pendingFeedbackReason && !looksLikeNewSearch(text)) {
        await submitFeedback({
          feedback_id: pendingFeedbackReason.feedbackId,
          reason: text,
          ui_language: pendingFeedbackReason.uiLanguage,
          user_id: sessionId,
        });
        setMessages((current) => [
          ...current,
          {
            id: `assistant-feedback-reason-${Date.now()}`,
            role: "assistant",
            text:
              pendingFeedbackReason.uiLanguage === "zh"
                ? "收到，我也把你的原因一起記下來了。"
                : "Got it. I logged your reason as well.",
            emptyState: null,
            picks: [],
          },
        ]);
        setPendingFeedbackReason(null);
        return;
      }

      if (false && pendingFeedbackReason) {
        setPendingFeedbackReason(null);
      }

      const moreRequest = parseMoreRequest(text);
      if (moreRequest) {
        const followUpMessage = await handleMoreRequest(
          moreRequest,
          lastRecommendationRequest,
          sessionId
        );
        setMessages((current) => [...current, followUpMessage]);
        if (followUpMessage.nextRecommendationRequest) {
          setLastRecommendationRequest(followUpMessage.nextRecommendationRequest);
        }
        return;
      }

      const payload = await fetchChatResponse(text, 3, [], sessionId);
      if (payload.needs_clarification && payload.clarification) {
        setMessages((current) => [
          ...current,
          buildClarificationMessage(payload.clarification),
        ]);
        setPendingClarification(payload.clarification);
        return;
      }
      const results = payload.results || [];
      setMessages((current) => [
        ...current,
        buildRecommendationMessage(payload, text, 3),
      ]);
      setLastRecommendationRequest({
        query: text,
        shownCount: Math.min(results.length, 3),
        parsedQuery: payload.parsed_query || {},
        seenIds: extractMovieIds(results),
        route: payload.route || "",
        recommendationId: payload.recommendation_id || "",
        uiLanguage: payload.ui_language || detectLanguage(text),
      });
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: `assistant-error-${Date.now()}`,
          role: "assistant",
          text: error.message || "Something went wrong while fetching recommendations.",
          emptyState: null,
          picks: [],
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  function handlePromptClick(prompt) {
    setInputValue(prompt);
  }

  return (
    <main className="app-shell">
      <section className="chat-panel">
        <header className="chat-header">
          <div className="header-topline">
            <div className="header-copy">
              <p className="eyebrow">Movie discovery assistant</p>
              <h1>Talk with MovieBot</h1>
            </div>
            <div className="top-tabs">
              <button className="tab tab-active" type="button">
                Chat
              </button>
              <button className="tab" type="button">
                Explore
              </button>
            </div>
          </div>
          <p className="subcopy">
            Describe a vibe, a favorite movie, or a mood, and get a few recommendation ideas.
          </p>
        </header>

        <section className="chat-body">
          <PromptChips prompts={prompts} onPromptClick={handlePromptClick} />
          <MessageList
            messages={messages}
            isLoading={isLoading}
            onOptionSelect={handleClarificationOptionSelect}
            onFeedbackSelect={handleFeedbackSelect}
            onFeedbackReasonSubmit={handleFeedbackReasonSubmit}
          />
        </section>

        <Composer
          value={inputValue}
          isLoading={isLoading}
          onChange={setInputValue}
          onSubmit={handleSubmit}
        />
      </section>
    </main>
  );

  async function handleClarificationOptionSelect(option, message) {
    if (!option || isLoading) {
      return;
    }

    const userMessage = {
      id: `user-clarification-${Date.now()}`,
      role: "user",
      text: option.label || option.name || option.role,
    };

    setMessages((current) => [...current, userMessage]);
    setIsLoading(true);

    try {
      const followUpMessage = await handleClarificationSelection(
        option,
        message.clarification,
        sessionId
      );
      setMessages((current) => [...current, followUpMessage]);
      if (followUpMessage.resolvedClarification) {
        setPendingClarification(null);
      }
      if (followUpMessage.nextRecommendationRequest) {
        setLastRecommendationRequest(followUpMessage.nextRecommendationRequest);
      }
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: `assistant-clarification-error-${Date.now()}`,
          role: "assistant",
          text: error.message || "Something went wrong while resolving that choice.",
          emptyState: null,
          picks: [],
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleFeedbackSelect(message, helpful) {
    if (!message?.id) {
      return;
    }

    updateMessageFeedback(message.id, {
      status: "submitting",
      choice: helpful ? "yes" : "no",
    });

    try {
      const response = await submitFeedback({
        helpful,
        recommendation_id: message.feedbackContext?.recommendationId || "",
        query: message.feedbackContext?.query || "",
        ui_language: message.feedbackContext?.uiLanguage || "en",
        route: message.feedbackContext?.route || "",
        parsed_query: message.feedbackContext?.parsedQuery || {},
        results: message.feedbackContext?.results || [],
        user_id: sessionId,
      });
      if (helpful) {
        updateMessageFeedback(message.id, {
          status: "positive",
          choice: "yes",
        });
        return;
      }
      updateMessageFeedback(message.id, {
        status: "awaiting_reason",
        choice: "no",
        feedbackId: response.feedback_id,
        reasonDraft: "",
        reasonError: "",
      });
      const uiLanguage = message.feedbackContext?.uiLanguage || "en";
      setMessages((current) => [
        ...current,
        {
          id: `assistant-feedback-followup-${Date.now()}`,
          role: "assistant",
          text:
            uiLanguage === "zh"
              ? "可以告訴我為什麼這次沒有幫到你嗎？如果你想直接繼續搜尋，也可以直接輸入下一個問題。"
              : "Could you tell me why these results did not help? If you want to continue, you can also just ask the next question.",
          emptyState: null,
          picks: [],
        },
      ]);
      setPendingFeedbackReason({
        feedbackId: response.feedback_id,
        uiLanguage,
      });
    } catch (error) {
      updateMessageFeedback(message.id, {
        status: "idle",
        choice: null,
      });
      setMessages((current) => [
        ...current,
        {
          id: `assistant-feedback-error-${Date.now()}`,
          role: "assistant",
          text: error.message || "Something went wrong while saving that feedback.",
          emptyState: null,
          picks: [],
        },
      ]);
    }
  }

  function updateMessageFeedback(messageId, feedbackState) {
    setMessages((current) =>
      current.map((message) =>
        message.id === messageId
          ? {
              ...message,
              feedback: {
                ...(message.feedback || {}),
                ...feedbackState,
              },
            }
          : message
        )
    );
  }

  async function handleFeedbackReasonSubmit(message, reasonText) {
    if (!message?.id || !reasonText.trim()) {
      return;
    }

    updateMessageFeedback(message.id, {
      status: "saving_reason",
      reasonDraft: reasonText,
      reasonError: "",
    });

    try {
      await submitFeedback({
        feedback_id: message.feedback?.feedbackId || message.feedbackContext?.recommendationId || "",
        reason: reasonText.trim(),
        ui_language: message.feedbackContext?.uiLanguage || "en",
        user_id: sessionId,
      });
      updateMessageFeedback(message.id, {
        status: "reason_saved",
        reasonDraft: "",
        reasonError: "",
      });
    } catch (error) {
      updateMessageFeedback(message.id, {
        status: "awaiting_reason",
        reasonDraft: reasonText,
        reasonError: error.message || "Something went wrong while saving your reason.",
      });
    }
  }
}

async function fetchChatResponse(text, topK = 3, excludeIds = [], userId = "") {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: text,
      top_k: topK,
      exclude_ids: excludeIds,
      user_id: userId,
    }),
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Request failed.");
  }
  return payload;
}

async function fetchClarifiedResponse(clarification, topK = 3, excludeIds = [], userId = "") {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      top_k: topK,
      exclude_ids: excludeIds,
      clarification,
      user_id: userId,
    }),
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Request failed.");
  }
  return payload;
}

async function submitFeedback(payload) {
  const response = await fetch("/api/feedback", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Feedback request failed.");
  }
  return data;
}

async function handleMoreRequest(moreRequest, lastRecommendationRequest, userId = "") {
  if (!lastRecommendationRequest?.query) {
    return {
      id: `assistant-more-missing-${Date.now()}`,
      role: "assistant",
      text: "Ask for a movie first, then I can show you more results.",
      emptyState: null,
      picks: [],
    };
  }

  const payload = await fetchChatResponse(
    lastRecommendationRequest.query,
    moreRequest.count,
    lastRecommendationRequest.seenIds || [],
    userId
  );
  const results = payload.results || [];
  const newResults = results.slice(0, moreRequest.count);

  if (!newResults.length) {
    return {
      id: `assistant-more-empty-${Date.now()}`,
      role: "assistant",
      text: buildNoMoreText(lastRecommendationRequest.parsedQuery || {}),
      emptyState: buildEmptyState("You have seen all available matches for this request."),
      picks: [],
    };
  }

  return {
    ...buildRecommendationMessage(
      {
        results: newResults,
        parsed_query: lastRecommendationRequest.parsedQuery || {},
        route: payload.route || lastRecommendationRequest.route || "",
        ui_language: payload.ui_language || lastRecommendationRequest.uiLanguage || "en",
        recommendation_id: payload.recommendation_id || "",
      },
      lastRecommendationRequest.query,
      moreRequest.count,
      buildMoreAssistantText(
        newResults.length,
        lastRecommendationRequest.parsedQuery || {},
        moreRequest.count
      )
    ),
    nextRecommendationRequest: {
      query: lastRecommendationRequest.query,
      shownCount: lastRecommendationRequest.shownCount + newResults.length,
      parsedQuery: lastRecommendationRequest.parsedQuery || {},
      seenIds: [...(lastRecommendationRequest.seenIds || []), ...extractMovieIds(newResults)],
      route: payload.route || lastRecommendationRequest.route || "",
      recommendationId: payload.recommendation_id || "",
      uiLanguage: payload.ui_language || lastRecommendationRequest.uiLanguage || "en",
    },
  };
}

async function handleClarificationInput(text, clarification, userId = "") {
  const option = resolveClarificationOption(text, clarification);
  if (!option) {
    return buildClarificationMessage(
      clarification,
      'I did not catch that. Choose one of these, or type "other".'
    );
  }
  return handleClarificationSelection(option, clarification, userId);
}

async function handleClarificationSelection(option, clarification, userId = "") {
  if (!clarification || !option) {
    throw new Error("Missing clarification context.");
  }

  if (option.role === "other") {
    return {
      id: `assistant-clarification-other-${Date.now()}`,
      role: "assistant",
      text: 'Tell me the full person and role you mean, like "director Christopher Nolan" or "cast Chris Evans".',
      emptyState: null,
      picks: [],
      resolvedClarification: true,
    };
  }

  const payload = await fetchClarifiedResponse(
    {
      original_message: clarification.original_message,
      role: option.role,
      name: option.name,
    },
    3,
    [],
    userId
  );
  const results = payload.results || [];
  return {
    ...buildRecommendationMessage(payload, clarification.original_message, 3),
    resolvedClarification: true,
    nextRecommendationRequest: {
      query: clarification.original_message,
      shownCount: Math.min(results.length, 3),
      parsedQuery: payload.parsed_query || {},
      seenIds: extractMovieIds(results),
      route: payload.route || "",
      uiLanguage: payload.ui_language || detectLanguage(clarification.original_message),
    },
  };
}

function buildPicks(results, limit = 3) {
  return results.slice(0, limit).map((movie, index) => ({
    title: movie.title || "Untitled",
    meta: buildMeta(movie),
    description: buildDescription(movie, index),
    featured: index === 0,
  }));
}

function buildMoreAssistantText(resultCount, parsedQuery = {}, requestedCount = resultCount) {
  const subject = buildMoreSubject(parsedQuery);
  const isPartial = resultCount < requestedCount;

  if (resultCount === 1) {
    if (isPartial) {
      return subject ? `I could only find 1 more ${subject}.` : "I could only find 1 more match.";
    }
    return subject ? `Here is 1 more ${subject}.` : "Here is 1 more match.";
  }

  if (isPartial) {
    return subject
      ? `I could only find ${resultCount} more ${subject}.`
      : `I could only find ${resultCount} more matches.`;
  }

  return subject ? `Here are ${resultCount} more ${subject}.` : `Here are ${resultCount} more matches.`;
}

function buildNoMoreText(parsedQuery = {}) {
  const subject = buildNoMoreSubject(parsedQuery);
  if (subject) {
    return `You have seen all available ${subject}.`;
  }
  return "You have seen all available matches for this request.";
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

function buildDescription(movie, index = 0) {
  if (movie.match_reason_text) {
    return movie.match_reason_text;
  }
  if (index === 0 && movie.top_pick_text) {
    return movie.top_pick_text;
  }
  if (movie.overview) {
    return movie.overview;
  }
  return "This is currently the strongest match from the recommendation pipeline.";
}

function buildWelcomeMessage() {
  const randomIndex = Math.floor(Math.random() * WELCOME_MESSAGES.length);
  return {
    id: "welcome-bot",
    role: "assistant",
    text: WELCOME_MESSAGES[randomIndex],
    emptyState: null,
    picks: [],
  };
}

function buildRecommendationMessage(payload, queryText, limit = 3, overrideText = "") {
  const results = payload.results || [];
  const uiLanguage = payload.ui_language || detectLanguage(queryText);
  return {
    id: `assistant-${Date.now()}`,
    role: "assistant",
    text: overrideText || (results.length ? buildAssistantText(results, uiLanguage) : buildNoMatchText(uiLanguage)),
    emptyState: results.length ? null : buildEmptyState(payload.reply_text),
    picks: buildPicks(results, limit),
    feedback: results.length ? buildFeedbackState(uiLanguage) : null,
    feedbackContext: results.length
      ? {
          query: queryText,
          route: payload.route || "",
          parsedQuery: payload.parsed_query || {},
          results,
          uiLanguage,
          recommendationId: payload.recommendation_id || "",
        }
      : null,
  };
}

function buildClarificationMessage(clarification, overrideText = "") {
  return {
    id: `assistant-clarification-prompt-${Date.now()}`,
    role: "assistant",
    text: overrideText || clarification.prompt,
    emptyState: null,
    picks: [],
    options: clarification.options || [],
    clarification,
  };
}

function pickRandomItems(items, count) {
  const shuffled = [...items];
  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(Math.random() * (index + 1));
    [shuffled[index], shuffled[randomIndex]] = [shuffled[randomIndex], shuffled[index]];
  }
  return shuffled.slice(0, count);
}

function parseMoreRequest(text) {
  const normalized = String(text).trim().toLowerCase();
  const patterns = [
    /^more$/,
    /^more\s+(\d{1,2})$/,
    /^(?:\d{1,2})\s+more$/,
    /^(?:other|another)\s+(\d{1,2})$/,
    /^(?:give me|show me|get me)\s+(?:other|another|more)\s+(\d{1,2})$/,
    /^(?:give me|show me|get me)\s+(\d{1,2})\s+more$/,
  ];

  for (const pattern of patterns) {
    const match = normalized.match(pattern);
    if (!match) {
      continue;
    }
    const count = match[1] ? Number.parseInt(match[1], 10) : 3;
    if (Number.isNaN(count) || count < 1) {
      return null;
    }
    return { count };
  }

  return null;
}

function resolveClarificationOption(text, clarification) {
  const normalized = normalizeChoiceText(text);
  if (!normalized) {
    return null;
  }

  if (normalized === "other") {
    return (clarification.options || []).find((option) => option.role === "other") || null;
  }

  const matches = (clarification.options || []).filter((option) => {
    const label = normalizeChoiceText(option.label);
    const role = normalizeChoiceText(option.role);
    const name = normalizeChoiceText(option.name);
    return normalized === label || normalized === role || normalized === name || name.includes(normalized);
  });

  return matches.length === 1 ? matches[0] : null;
}

function normalizeChoiceText(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function buildEmptyState(replyText) {
  return {
    hint: replyText || "Try changing the year, language, actor, or director filters.",
  };
}

function buildAssistantText(results, uiLanguage = "en") {
  if (!results.length) {
    return buildNoMatchText(uiLanguage);
  }
  if (results.length === 1) {
    return uiLanguage === "zh"
      ? "我找到一個很符合你需求的選項。"
      : "I found one strong match for this request.";
  }
  return uiLanguage === "zh"
    ? "我先整理了幾個可能適合你的選項，並把最強的一個放在最前面。"
    : "Here are a few matches. I highlighted the strongest pick first.";
}

function buildNoMatchText(uiLanguage = "en") {
  return uiLanguage === "zh"
    ? "我暫時找不到很強的匹配結果。"
    : "I could not find a strong match for that request.";
}

function buildFeedbackState(uiLanguage = "en") {
  return {
    status: "idle",
    choice: null,
    prompt: uiLanguage === "zh" ? "這次的結果有幫到你嗎？" : "Did these results help you?",
    yesLabel: uiLanguage === "zh" ? "有" : "Yes",
    noLabel: uiLanguage === "zh" ? "沒有" : "No",
    positiveText: uiLanguage === "zh" ? "已收到，太好了。" : "Noted. Glad it helped.",
    negativeText: "",
    loadingText: uiLanguage === "zh" ? "正在記錄..." : "Saving feedback...",
  };
}

function getOrCreateSessionId() {
  if (typeof window === "undefined") {
    return "anonymous";
  }

  const storageKey = "moviebot_session_id";
  const existingValue = window.localStorage.getItem(storageKey);
  if (existingValue) {
    return existingValue;
  }

  const newValue =
    typeof window.crypto?.randomUUID === "function"
      ? window.crypto.randomUUID()
      : `session-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  window.localStorage.setItem(storageKey, newValue);
  return newValue;
}

function detectLanguage(text) {
  return /[\u4e00-\u9fff]/.test(String(text || "")) ? "zh" : "en";
}

function looksLikeNewSearch(text) {
  const normalized = String(text || "").trim().toLowerCase();
  if (!normalized) {
    return false;
  }
  if (parseMoreRequest(normalized)) {
    return true;
  }
  return [
    "movie",
    "movies",
    "recommend",
    "something like",
    "similar to",
    "genre",
    "actor",
    "director",
    "franchise",
    "電影",
    "想看",
    "推薦",
    "一部",
    "片",
  ].some((token) => normalized.includes(token));
}

function extractMovieIds(results) {
  return results
    .map((movie) => movie?.id)
    .filter((value) => value !== null && value !== undefined);
}

function buildMoreSubject(parsedQuery) {
  const cast = String(parsedQuery.cast || "").trim();
  if (cast) {
    return `${cast} pick${cast.endsWith("s") ? "" : "s"}`;
  }

  const director = String(parsedQuery.director || "").trim();
  if (director) {
    return `${director} films`;
  }

  const genre = String(parsedQuery.genre || "").trim();
  if (genre) {
    return `${genre.toLowerCase()} movies`;
  }

  const keywords = String(parsedQuery.keywords || "").trim();
  if (keywords) {
    return `${keywords.toLowerCase()} picks`;
  }

  const semanticQuery = String(parsedQuery.semantic_query || "").trim();
  if (semanticQuery) {
    return "matches";
  }

  return "";
}

function buildNoMoreSubject(parsedQuery) {
  const cast = String(parsedQuery.cast || "").trim();
  if (cast) {
    return `${cast} matches`;
  }

  const director = String(parsedQuery.director || "").trim();
  if (director) {
    return `${director} films`;
  }

  const genre = String(parsedQuery.genre || "").trim();
  if (genre) {
    return `${genre.toLowerCase()} movies`;
  }

  const keywords = String(parsedQuery.keywords || "").trim();
  if (keywords) {
    return `${keywords.toLowerCase()} matches`;
  }

  return "";
}
