import { Slot } from "@radix-ui/react-slot";
import { type VariantProps, cva } from "class-variance-authority";

import { cn } from "@/lib/format/cn";

const badgeVariants = cva(
  "inline-flex items-center justify-center gap-1 rounded-[var(--radius-pill)] border px-2.5 py-0.5 text-xs font-medium transition-colors [&_svg]:size-3",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-transparent bg-surface text-foreground",
        outline: "border-border text-foreground",
        trusted: "border-transparent bg-signal-verified/10 text-signal-verified",
        caution: "border-transparent bg-signal-caution/10 text-signal-caution",
        danger: "border-transparent bg-signal-danger/10 text-signal-danger",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

function Badge({
  className,
  variant,
  asChild = false,
  ...props
}: React.ComponentProps<"span"> & VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "span";
  return (
    <Comp data-slot="badge" className={cn(badgeVariants({ variant, className }))} {...props} />
  );
}

export { Badge, badgeVariants };
