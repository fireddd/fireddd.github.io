# fireddd.github.io

Personal site for **Shubhransh Jagota** — software engineer, distributed AI systems.
Live at **<https://fireddd.github.io/>**.

Static HTML, no build step, no JavaScript. Edit and push; GitHub Pages serves `main`.

## Why it's built this way

AI crawlers do not execute JavaScript. GPTBot and ClaudeBot download JS files but never
run them ([Vercel/MERJ, ~500M requests](https://vercel.com/blog/the-rise-of-the-ai-crawler)).
A client-rendered portfolio is therefore *invisible* to ChatGPT, Claude and Perplexity —
so every fact here lives in the raw HTML bytes, not in a hydration payload.

## Layout

| File           | Purpose                                                                 |
| -------------- | ----------------------------------------------------------------------- |
| `index.html`   | The page. Contains a `Person` + `ProfilePage` + `WebSite` JSON-LD graph. |
| `resume.json`  | Full CV in [JSON Resume](https://jsonresume.org/schema) schema v1.0.0.   |
| `index.md`     | Markdown mirror of the page — what agents get the cleanest read from.    |
| `llms.txt`     | Summary + link index, per [llmstxt.org](https://llmstxt.org/).           |
| `robots.txt`   | Explicitly **allows** every AI crawler. Inverted from the usual advice.  |
| `sitemap.xml`  | Four URLs.                                                              |
| `.nojekyll`    | Stops Jekyll compiling `index.md` over the top of `index.html`.          |

## When you update your résumé

Change the facts in **`index.html`**, **`resume.json`** and **`index.md`** together, and bump
`dateModified` in the JSON-LD, `meta.lastModified` in `resume.json`, and the dates in
`sitemap.xml`. Consistency across the three is what makes an LLM confident rather than
hedging — divergence is what makes it hallucinate.

Keep your name, job title and location byte-identical here, on LinkedIn, and on your GitHub
profile. That consistency is the single highest-leverage thing for entity resolution.
