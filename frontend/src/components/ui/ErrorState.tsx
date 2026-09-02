import { cn } from "../../utils";

interface ErrorStateProps {
  title?: string;
  message: string;
  retry?: () => void;
  className?: string;
}

export function ErrorState({
  title = "Something went wrong",
  message,
  retry,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-red-200 bg-red-50 px-6 py-12 text-center",
        className,
      )}
    >
      <p className="text-base font-semibold text-red-800">{title}</p>
      <p className="mt-1 max-w-md text-sm text-red-700">{message}</p>
      {retry && (
        <button
          type="button"
          onClick={retry}
          className="mt-4 text-sm font-medium text-red-800 underline hover:text-red-900"
        >
          Try again
        </button>
      )}
    </div>
  );
}
