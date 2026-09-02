import type { InputHTMLAttributes, ReactNode } from "react";
import { cn } from "../../utils";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  inputClassName?: string;
}

export function Input({
  label,
  error,
  hint,
  id,
  className,
  inputClassName,
  ...props
}: InputProps) {
  const inputId = id ?? props.name;
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      {label && (
        <label
          htmlFor={inputId}
          className="text-sm font-medium text-slate-700"
        >
          {label}
        </label>
      )}
      <input
        id={inputId}
        aria-invalid={!!error}
        aria-describedby={
          error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined
        }
        className={cn(
          "w-full rounded-lg border bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 transition-colors",
          "focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent",
          error
            ? "border-red-500"
            : "border-slate-300 hover:border-slate-400",
          inputClassName,
        )}
        {...props}
      />
      {hint && !error && (
        <p id={`${inputId}-hint`} className="text-xs text-slate-500">
          {hint}
        </p>
      )}
      {error && (
        <p
          id={`${inputId}-error`}
          role="alert"
          className="text-xs font-medium text-red-600"
        >
          {error}
        </p>
      )}
    </div>
  );
}

interface FieldsetProps {
  legend?: string;
  children: ReactNode;
  className?: string;
}

export function Fieldset({ legend, children, className }: FieldsetProps) {
  return (
    <fieldset className={cn("flex flex-col gap-4", className)}>
      {legend && (
        <legend className="mb-1 text-lg font-semibold text-slate-900">
          {legend}
        </legend>
      )}
      {children}
    </fieldset>
  );
}
