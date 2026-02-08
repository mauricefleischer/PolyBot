# PolyBot - Polymarket Consensus Terminal

A professional whale tracking and consensus aggregation terminal for Polymarket, featuring Kelly Criterion position sizing.

## Features

- 🐋 **Whale Tracking** - Track multiple whale wallets and aggregate their positions
- 📊 **Consensus Signals** - See which markets have multiple whales aligned
- 🧮 **Becker Alpha Score** - Proprietary scoring algorithm for signal quality
- 💰 **Kelly Criterion Sizing** - Mathematically optimal position sizing
- ⚙️ **Risk Configuration** - Adjust aggressiveness, max risk, and filters
- 🔄 **Live Updates** - 5-second polling for real-time data

## Tech Stack

- **Backend**: Python 3.9+, FastAPI, httpx, cachetools
- **Frontend**: React 18, TypeScript, TanStack Query, Tailwind CSS
- **API**: Polymarket Data API & Gamma API

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/signals` | Ranked consensus signals with Kelly sizing |
| `GET /api/v1/user/portfolio` | User portfolio vs whale consensus |
| `GET /api/v1/config/wallets` | List tracked wallets |
| `POST /api/v1/config/wallets` | Add/remove tracked wallets |

## Alpha Scoring

| Component | Points |
|-----------|--------|
| Base | 50 |
| Smart Short (NO) | +20 |
| Longshot Penalty | -30 |
| Extreme Favorite | +10 |
| High Conviction | +10 |

## License

MIT
