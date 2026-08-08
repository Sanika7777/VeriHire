import { cn } from "@/lib/format/cn";

function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      className={cn("animate-pulse rounded-[var(--radius-control)] bg-border", className)}
      {...props}
    />
  );
}

export { Skeleton };
