<p align = "center" draggable="false" ><img src="https://github.com/AI-Maker-Space/LLM-Dev-101/assets/37101144/d1343317-fa2f-41e1-8af1-1dbb18399719" 
     width="200px"
     height="auto"/>
</p>

## <h1 align="center" id="heading">🚀 Welcome to the AI Engineer Challenge</h1>

### 🎯 Build Your First Startup Mentor AI with RAG Superpowers!

> **New to this?** No worries! Check out our [Setup Guide](docs/GIT_SETUP.md) to get your dev environment ready to rock! 🛠️

> **Want more context?** Dive into our [Interactive Dev Environment for LLM Development](https://github.com/AI-Maker-Space/Interactive-Dev-Environment-for-AI-Engineers) for the full experience! 🌟

Hey there, future AI engineer! 👋 Ready to build something absolutely awesome? You're about to create a **smart startup mentor AI** that can:

- 💬 **Chat intelligently** about entrepreneurship and business strategy
- 📄 **Analyze PDF documents** with RAG (Retrieval Augmented Generation) 
- 🧠 **Combine document insights** with general startup knowledge
- 🎨 **Look stunning** with a modern Next.js frontend
- 🚀 **Deploy instantly** to the web with Vercel

**What makes this special?** Your AI won't just be another chatbot - it's a specialized startup mentor that only talks business! Upload your business plans, pitch decks, or company docs, and watch it provide targeted advice based on your specific content. 🎯

Ready to dive in? Let's build something incredible! 💪

---

<details>
  <summary>🤖 Step 1: Get Cozy with GPT-4o-mini (Your AI Sidekick)</summary>

Before we build our app, let's understand how to talk to GPT like a pro developer! 

1. **Jump into this interactive notebook** → [GPT-4o-mini Developer Tutorial](https://colab.research.google.com/drive/1sT7rzY_Lb1_wS0ELI1JJfff0NUEcSD72?usp=sharing) 

2. **Experiment with prompts** - Try different system messages and see how the AI responds

3. **Get that "aha!" moment** when you realize how powerful prompt engineering can be 💡

**Pro tip:** The better you understand how to prompt AI, the cooler your app will be! 

</details>

<details>
  <summary>🍴 Step 2: Fork & Clone Like a Boss</summary>

Time to get this bad boy on your machine! Here's your mission:

**Prerequisites Checklist:**
- ✅ GitHub account (obviously!)
- ✅ Git installed and ready to roll
- ✅ Your favorite code editor (Cursor is 🔥)
- ✅ Terminal access (time to feel like a hacker!)
- ✅ GitHub Personal Access Token (for the authentication magic)

**Let's do this:**

1. **Fork this repo** like you mean it! 
   
   ![Fork it real good](https://i.imgur.com/bhjySNh.png)

2. **Clone your shiny new repo:**

   ```bash
   # Navigate to your favorite coding spot
   cd PATH_TO_YOUR_CODING_PARADISE

   # Clone it! (This creates The-AI-Engineer-Challenge folder)
   git clone git@github.com:<YOUR_GITHUB_USERNAME>/The-AI-Engineer-Challenge.git
   ```

   > **SSH not working?** No stress! Use HTTPS instead: `https://github.com/<YOUR_USERNAME>/The-AI-Engineer-Challenge.git`

3. **Verify everything's connected:**

   ```bash
   # Check your remotes (should show your fork)
   git remote -v

   # Make sure git is happy
   git status

   # See what branch you're vibing on
   git branch
   ```

4. **Open it in Cursor and prepare to be amazed:**

   ```bash
   cd The-AI-Engineer-Challenge
   cursor .
   ```

5. **Peek at the backend magic** in `/api/app.py` - this is where the FastAPI awesomeness lives! 🐍

</details>

<details>
  <summary>🎨 Step 3: Set Up Your Vibe-Coding Environment</summary>

Okay, this might seem backwards (setup before coding?!), but trust us - this small investment will make your vibe-coding experience absolutely stellar! 🌟

**Why we're doing this:** We're bridging AI-Assisted Development with pure Vibe-Coding magic. Just a tiny bit of setup for maximum coding superpowers!

1. **Customize your rules** in `.cursor/rules/` 
   - Add your favorite color schemes to `frontend-rule.mdc`
   - Go wild with your creative vision! 🎨

2. **Index some docs** (this is where the magic happens):
   - Hit `CTRL+SHIFT+P` (or `CMD+SHIFT+P` on Mac)
   - Type "custom doc" and feel the power!
   
   ![Custom doc indexing](https://i.imgur.com/ILx3hZu.png)

3. **Add Next.js docs** to your AI's brain:
   - Paste `https://nextjs.org/docs` into the prompt
   
   ![Next.js docs](https://i.imgur.com/psBjpQd.png)

4. **Use default configs** and watch the docs get indexed:
   
   ![Default configs](https://i.imgur.com/LULLeaF.png)

5. **Repeat with Vercel docs** for deployment superpowers!
   
   ![Vercel docs indexed](https://i.imgur.com/hjyXhhC.png) 

**Result:** Your AI assistant now knows Next.js and Vercel like a seasoned developer! 🧠✨

</details>

<details>
  <summary>🎯 Step 4: Vibe-Code Your Startup Mentor Frontend</summary>

This is where the real fun begins! Time to create a beautiful, functional frontend that'll make your startup mentor AI shine! ✨

**What you're building:**
- 🎨 A gorgeous chat interface for startup mentoring
- 📤 PDF upload with drag-and-drop (because we're fancy like that)
- 🔍 Document management and stats
- 💡 Smart validation for business content only
- 📱 Mobile-responsive design that looks amazing everywhere

**Let's vibe-code:**

1. **Open Cursor chat** with `Command-L` or `CTRL-L`

2. **Configure your chat settings** for maximum AI power:
   
   ![Chat settings](https://i.imgur.com/LSgRSgF.png)

3. **Start the conversation:** Ask Cursor to enhance the existing frontend with RAG capabilities! Try something like:
   ```
   "Help me improve this Next.js frontend to work with the RAG-enabled startup mentor backend. I want a beautiful chat interface with PDF upload, document management, and mobile-responsive design!"
   ```

4. **Iterate like a pro:** Keep refining until it's perfect! 
   - Not happy with the colors? Ask for changes!
   - Want different animations? Go for it!
   - Need better mobile experience? Just ask!

5. **Run your creation:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

**Pro tip:** Copy any errors back to Cursor and ask it to fix them. It's like having a senior developer pair programming with you! 🤝

</details>

<details>
  <summary>🚀 Step 5: Deploy Your Masterpiece to the World</summary>

Time to share your creation with the world! Let's get this baby live on the internet! 🌐

**Prerequisites:**
- ✅ Vercel account (sign up with your GitHub - it's free!)
- ✅ `npm` installed (probably happened in the previous step)

**Deployment magic:**

1. **Install Vercel CLI globally:**
   ```bash
   npm install -g vercel
   ```

2. **Deploy with one command:**
   ```bash
   vercel
   ```

3. **Follow the prompts** (Vercel makes it super easy):
   
   ![Vercel deployment](https://i.imgur.com/D1iKGCq.png)

4. **Get your live link** and share it with everyone! 🎉

**Important:** Make sure to share your *domain* link for public access:

![Domain link](https://i.imgur.com/mpXIgIz.png)

**Test tip:** Open your deployed app in an incognito tab to make sure it works for everyone! 🕵️

</details>

---

## 🎊 You Did It! Time to Celebrate!

**Congratulations, AI Engineer!** 🏆 You just built and deployed a sophisticated RAG-powered startup mentor AI! That's seriously impressive! 🚀

### 🌟 What You've Accomplished:
- ✅ Built a full-stack AI application
- ✅ Implemented RAG (Retrieval Augmented Generation)
- ✅ Created a beautiful, responsive frontend
- ✅ Added intelligent document processing
- ✅ Deployed to production
- ✅ Became an AI Engineer! 🎯

### 📢 Share Your Success!

Get on LinkedIn and show off your amazing work! Tag us **@AIMakerspace** - we love seeing what our community builds! 

**Here's a template to get you started:**

```
🚀🎉 JUST SHIPPED MY FIRST AI APPLICATION! 🎉🚀

🏗️ I'm thrilled to announce that I've successfully built and deployed a RAG-powered Startup Mentor AI using Next.js, FastAPI, and OpenAI! This isn't just any chatbot - it's a specialized business advisor that analyzes uploaded documents and provides targeted startup advice! 🧠💼

✨ Features:
📄 PDF document analysis with RAG
💬 Intelligent startup mentoring
🎨 Beautiful, responsive UI
🚀 Live deployment on Vercel

Check it out 👇
[YOUR_AWESOME_APP_LINK]

Huge thanks to @AI Makerspace for the incredible challenge and community support! The journey from idea to deployment was absolutely amazing! 🤗🙏

Who else is building cool AI stuff? Let's connect and share ideas! 🌐💡

#AIEngineering #RAG #StartupAI #NextJS #OpenAI #FirstAIApp #AIMakerspace
```

### 🔥 What's Next?

- **Experiment with different AI models**
- **Add more document types** (Word, PowerPoint, etc.)
- **Create specialized prompts** for different business areas
- **Build additional features** like document summarization
- **Join our community** and help others on their AI journey!

**Keep building, keep learning, and keep being awesome!** 🌟
