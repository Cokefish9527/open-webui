export interface ScenarioContext {
  auth?: {
    email: string;
    tenantId: string;
    token?: string;
  };
  strategy?: {
    strategyId?: string;
    roadmapVersion?: string;
  };
  materials?: Array<{ id: string; type: string; ossPath?: string }>;
  workflow?: {
    cardId?: string;
    taskId?: string;
    videoId?: string;
    lastEvent?: string;
  };
  publish?: {
    jobId?: string;
    platforms?: string[];
  };
  analytics?: {
    snapshotAt?: string;
    metrics?: Record<string, number>;
  };
}

export function createEmptyContext(): ScenarioContext {
  return {
    materials: [],
  };
}

export function mergeContext(target: ScenarioContext, patch: Partial<ScenarioContext>): ScenarioContext {
  Object.assign(target, patch);
  return target;
}
