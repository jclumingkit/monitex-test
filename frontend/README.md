# Monitex Operator Dashboard

This Next.js application provides the operator interface for the Monitex
security-event processing demo.

## Features

- Live alert delivery over server-sent events (SSE), including severity updates
  produced by backend correlation.
- Paginated event feed with severity ordering, status filters, and date ranges.
- Detailed event view with detection metadata and available snapshots.
- Individual and bulk actions for acknowledging or resolving alerts.
- New-event indicators and automatic cache updates for incoming alerts.
- Per-site event timelines at `/site/{siteId}`, ordered from the oldest source
  event to the newest and loaded automatically as the page is scrolled.

## Getting Started

Install dependencies and start the development server:

```bash
npm install
npm run dev
```

Open [http://localhost:3000/dashboard](http://localhost:3000/dashboard). The
backend must also be running; see `../backend/README.md` for its setup.

## Configuration

The frontend uses `http://localhost:8000` by default. Set these variables when
the backend is available at another origin:

```bash
BACKEND_URL="http://localhost:8000"
NEXT_PUBLIC_BACKEND_URL="http://localhost:8000"
```

`BACKEND_URL` is used by server actions for queries and status updates.
`NEXT_PUBLIC_BACKEND_URL` is used by the browser for the live SSE connection.

## Routes

- `/dashboard` displays the live operator event feed and event details.
- `/site/{siteId}` displays the paginated timeline for one site. Site IDs in the
  event details panel link directly to this route.

## Commands

```bash
npm run dev
npm run lint
npm run build
npm run start
```

The application uses Next.js 16, React 19, TanStack Query, Tailwind CSS, Base UI,
and shadcn components.
