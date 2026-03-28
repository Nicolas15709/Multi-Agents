function estimateChars(messages = []) {
  return messages.reduce((sum, m) => sum + (m.content?.length || 0) + (m.summary?.length || 0), 0);
}

export function buildSlidingWindowContext(messages, options = {}) {
  const maxChars = options.maxChars ?? 280000;
  const recentMessages = options.recentMessages ?? 18;
  const pinnedTypes = new Set(options.keepPinnedTypes ?? []);

  const pinned = messages.filter((m) => m.pinned || pinnedTypes.has(m.message_type));
  const unpinned = messages.filter((m) => !(m.pinned || pinnedTypes.has(m.message_type)));

  const recent = unpinned.slice(-recentMessages);
  const older = unpinned.slice(0, Math.max(0, unpinned.length - recentMessages));

  const compactedOlder = older.map((m) => ({
    ...m,
    content: m.summary || `[summarized ${m.message_type}]`
  }));

  let result = [...pinned, ...compactedOlder, ...recent];

  while (estimateChars(result) > maxChars && result.length > pinned.length + 1) {
    const removableIndex = result.findIndex((m) => !(m.pinned || pinnedTypes.has(m.message_type)));
    if (removableIndex === -1) break;
    result.splice(removableIndex, 1);
  }

  return result;
}
