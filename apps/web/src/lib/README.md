# Web infrastructure

Transport and shared session helpers live here. Business workflows belong in features. This directory must not import features. `api/transport.ts` holds access credentials only in an instance's memory, coalesces refresh requests, and calls FastAPI through generated types. TanStack Query stores account results, never tokens; its client belongs to the mounted private shell and is cleared on account transitions.
