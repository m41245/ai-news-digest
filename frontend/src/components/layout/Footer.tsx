export function Footer() {
  return (
    <footer className="mt-20 border-t border-slate-200 bg-white">
      <div className="container-page flex flex-col items-center justify-between gap-4 py-8 sm:flex-row">
        <p className="text-sm text-slate-500">
          &copy; {new Date().getFullYear()} AI News Digest. All rights reserved.
        </p>
        <nav aria-label="Footer" className="flex gap-6">
          <a href="/news" className="text-sm text-slate-500 hover:text-slate-900">
            News
          </a>
          <a href="/digests" className="text-sm text-slate-500 hover:text-slate-900">
            Digests
          </a>
          <a href="/categories" className="text-sm text-slate-500 hover:text-slate-900">
            Categories
          </a>
          <a href="/privacy" className="text-sm text-slate-500 hover:text-slate-900">
            Privacy
          </a>
          <a href="/terms" className="text-sm text-slate-500 hover:text-slate-900">
            Terms
          </a>
        </nav>
      </div>
    </footer>
  );
}
