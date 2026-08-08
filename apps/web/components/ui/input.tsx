import { cn } from "@/lib/format/cn";

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "flex h-10 w-full rounded-[var(--radius-control)] border border-border bg-surface-0 px-3 py-2 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus-visible:border-primary disabled:cursor-not-allowed disabled:opacity-50",
        "aria-invalid:border-signal-danger",
        className,
      )}
      {...props}
    />
  );
}

export { Input };
