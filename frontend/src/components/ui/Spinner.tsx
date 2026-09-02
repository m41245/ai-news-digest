import { cn } from "../../utils";

interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  className?: string;
  label?: string;
}

const SIZES = { sm: "h-4 w-4 border-2", md: "h-8 w-8 border-2", lg: "h-12 w-12 border-3" };

export function Spinner({ size = "md", className, label = "Loading" }: SpinnerProps) {
  return (
    <div
      className={cn("flex items-center justify-center", className)}
      role="status"
      aria-label={label}
    >
      <div
        className={cn(
          "animate-spin rounded-full border-brand-500 border-t-transparent",
          SIZES[size],
        )}
      />
      <span className="sr-only">{label}</span>
    </div>
  );
}
