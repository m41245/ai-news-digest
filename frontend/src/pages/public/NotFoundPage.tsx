import { Link } from "react-router-dom";
import { Seo } from "../../components/Seo";

export function NotFoundPage() {
  return (
    <>
      <Seo title="Page not found" noindex />
      <div className="container-page flex min-h-[50vh] flex-col items-center justify-center py-16 text-center">
        <p className="text-sm font-semibold text-brand-600">404</p>
        <h1 className="mt-2 text-3xl font-bold text-slate-900">Page not found</h1>
        <p className="mt-2 max-w-md text-slate-600">
          The page you are looking for does not exist or has moved.
        </p>
        <Link
          to="/"
          className="mt-6 inline-flex rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-brand-700"
        >
          Go back home
        </Link>
      </div>
    </>
  );
}
