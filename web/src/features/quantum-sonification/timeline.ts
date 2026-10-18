import type { AudioSegment, GraphAudioEvent, GraphBackboneLayer, SonificationMode } from "./types";

/** Half-open intervals assign shared boundaries to the NEW layer. Gaps remain gaps. */
export function segmentAt(segments: AudioSegment[], time: number) {
  // HTML media clocks may round a CSV's sample-accurate boundary to microseconds.
  const epsilon = 1e-6;
  return segments.find((segment, index) => time >= segment.start_sec - epsilon && (
    time < segment.end_sec - epsilon || (index === segments.length - 1 && Math.abs(time - segment.end_sec) <= epsilon)
  )) || null;
}

/** Convert the supplied floating-point event durations to renderer sample slots. */
export function sampleAlignedEvents(events: GraphAudioEvent[], sampleRate: number) {
  let cursor = 0;
  return events.map(event => {
    const length = Math.max(1, Math.round((event.end - event.start) * sampleRate));
    const aligned = { ...event, start: cursor / sampleRate, end: (cursor + length) / sampleRate };
    cursor += length;
    return aligned;
  });
}

export function traversalMoment(graph: GraphBackboneLayer | null, segment: AudioSegment | null, mode: SonificationMode, time: number, sampleRate: number) {
  const branches = mode === "mix" ? ["bfs", "dfs"] as const : [mode] as const;
  const localTime = segment ? time - segment.start_sec : null;
  const schedules = branches.map(branch => {
    const events = sampleAlignedEvents(graph?.events?.[branch] || [], sampleRate);
    return { branch, events, duration: events.at(-1)?.end || 0 };
  });
  const duration = Math.max(0, ...schedules.map(schedule => schedule.duration));
  const compatible = Boolean(graph && segment && graph.layer === segment.layer && duration > 0 && Math.abs(duration - (segment.end_sec - segment.start_sec)) <= 2 / sampleRate);
  const active = compatible && localTime !== null ? schedules.flatMap(schedule => schedule.events
    .map((event, index) => ({ branch: schedule.branch, event, index }))
    .filter(({ event }) => localTime >= event.start && localTime < event.end)) : [];
  return { localTime, compatible, schedules, active, activeNodes: [...new Set(active.filter(item => item.event.kind === "sound").flatMap(item => item.event.nodes))] };
}
