import { json } from '@sveltejs/kit';
import { dev } from '$app/environment';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import type { RequestHandler } from './$types';

// Resolve the folder Chrome should map; default to repo root unless overridden.
const WORKSPACE_ROOT = path.resolve(
	process.env.CHROME_DEVTOOLS_WORKSPACE_ROOT ?? process.cwd()
);

// Chrome prefers a stable UUID, so allow overriding while keeping a per-process fallback.
const WORKSPACE_UUID = process.env.CHROME_DEVTOOLS_WORKSPACE_UUID ?? randomUUID();

export const GET: RequestHandler = () => {
	if (!dev) {
		return new Response(null, { status: 404 });
	}

	return json({
		workspace: {
			root: WORKSPACE_ROOT,
			uuid: WORKSPACE_UUID
		}
	});
};
