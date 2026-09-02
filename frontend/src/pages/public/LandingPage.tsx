import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";

export function LandingPage() {
  return (
    <>
      <Helmet>
        <title>AI News Digest</title>
        <meta
          name="description"
          content="AI-powered news aggregation, summarization, and daily digests. Stay informed with curated, categorized news delivered in a clear, readable format."
        />
      </Helmet>
      <section className="container-page py-20 sm:py-28">
        <div className="mx-auto max-w-3xl text-center">
          <span className="inline-flex items-center rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700">
            AI-powered news, curated daily
          </span>
          <h1 className="mt-6 text-4xl font-bold tracking-tight text-slate-900 sm:text-6xl">
            News, distilled by AI.
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-slate-600">
            AI News Digest aggregates articles from trusted sources, summarizes
            them with AI, and delivers clear, categorized daily digests so you
            can stay informed without the noise.
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
            <Link
              to="/news"
              className="inline-flex items-center justify-center rounded-lg bg-brand-600 px-5 py-2.5 text-base font-medium text-white shadow-sm transition-colors hover:bg-brand-700"
            >
              Browse the latest news
            </Link>
            <Link
              to="/digests"
              className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-base font-medium text-slate-900 shadow-sm transition-colors hover:bg-slate-50"
            >
              View digests
            </Link>
          </div>
        </div>
      </section>

      <section className="border-t border-slate-200 bg-slate-50 py-16">
        <div className="container-page">
          <div className="mx-auto mb-10 max-w-2xl text-center">
            <h2 className="text-2xl font-bold text-slate-900">How it works</h2>
            <p className="mt-2 text-slate-600">
              From raw feeds to a readable digest in four steps.
            </p>
          </div>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                t: "Aggregate",
                d: "Pulls articles from multiple trusted RSS sources.",
              },
              {
                t: "Summarize",
                d: "AI produces concise summaries for every article.",
              },
              {
                t: "Categorize",
                d: "Articles are organized into clear categories.",
              },
              {
                t: "Digest",
                d: "A daily digest delivers the signal, not the noise.",
              },
            ].map((step) => (
              <div
                key={step.t}
                className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
              >
                <h3 className="text-base font-semibold text-slate-900">
                  {step.t}
                </h3>
                <p className="mt-1 text-sm text-slate-600">{step.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="container-page py-16">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-2xl font-bold text-slate-900">
            Ready to cut through the noise?
          </h2>
          <p className="mt-2 text-slate-600">
            Explore the latest articles and digests, or sign up for a
            personalized experience.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              to="/news"
              className="inline-flex items-center justify-center rounded-lg bg-brand-600 px-5 py-2.5 text-base font-medium text-white shadow-sm transition-colors hover:bg-brand-700"
            >
              Explore news
            </Link>
            <Link
              to="/register"
              className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-base font-medium text-slate-900 shadow-sm transition-colors hover:bg-slate-50"
            >
              Create an account
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
