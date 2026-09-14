import { Link } from "react-router-dom";

export function Footer() {
  return (
    <footer className="mt-20 border-t border-slate-200 bg-white">
      <div className="container-page flex flex-col items-center justify-between gap-4 py-8 sm:flex-row">
        <p className="text-sm text-slate-500">
          &copy; {new Date().getFullYear()} AI News Digest. All rights reserved.
        </p>
        <nav aria-label="Footer" className="flex gap-6">
          <Link to="/news" className="text-sm text-slate-500 hover:text-slate-900">
            News
          </Link>
          <Link to="/digests" className="text-sm text-slate-500 hover:text-slate-900">
            Digests
          </Link>
          <Link to="/categories" className="text-sm text-slate-500 hover:text-slate-900">
            Categories
          </Link>
          <Link to="/privacy" className="text-sm text-slate-500 hover:text-slate-900">
            Privacy
          </Link>
          <Link to="/terms" className="text-sm text-slate-500 hover:text-slate-900">
            Terms
          </Link>
        </nav>
      </div>
    </footer>
  );
}
