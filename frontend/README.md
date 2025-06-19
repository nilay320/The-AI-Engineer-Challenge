# 🚀 Startup Mentor AI Frontend

Welcome to the Startup Mentor AI frontend! This is your friendly, research-backed AI mentor for all things startup. Ask questions, get actionable advice, and build your dream company with a little help from AI magic.

## Getting Started (Locally)

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```
2. **Run the development server:**
   ```bash
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000) in your browser to see the app.

3. **Make sure the backend is running!**
   - The frontend expects the FastAPI backend to be running and accessible at `/api` (e.g., [http://localhost:8000/api](http://localhost:8000/api)).
   - See the backend README for setup instructions.

## Deploying to Vercel

1. Push your code to GitHub (or your favorite git provider).
2. Go to [Vercel](https://vercel.com/) and import your project.
3. Set up a Vercel rewrite so that `/api/*` routes are proxied to your FastAPI backend.
4. Deploy and share your AI mentor with the world!

## Features
- Chat with an AI mentor about startup best practices
- Clean, friendly, and responsive UI
- No API key required on the frontend (it's handled securely in the backend)

## Have fun, and may your startup dreams take flight! 🦄
