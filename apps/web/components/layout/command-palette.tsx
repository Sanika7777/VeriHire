"use client";

import { useRouter } from "next/navigation";
import { Building2, LayoutDashboard, LogIn, Search, UserRound } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { useCurrentUser } from "@/lib/auth/use-auth";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { useSearch } from "@/lib/search/use-search";

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebouncedValue(query, 250);
  const router = useRouter();
  const { data: user } = useCurrentUser();
  const { data: results } = useSearch({ q: debouncedQuery });

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  const go = (path: string) => {
    setOpen(false);
    setQuery("");
    router.push(path);
  };

  const detailPath = (item: { subject_type: string; id: string }) =>
    item.subject_type === "recruiter"
      ? `/recruiters/${item.id}`
      : item.subject_type === "job_posting"
        ? `/postings/${item.id}`
        : `/companies/${item.id}`;

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(true)}
        className="gap-2 text-muted-foreground"
      >
        <Search className="size-4" />
        <span className="hidden sm:inline">Search</span>
        <kbd className="hidden rounded border border-border bg-surface px-1.5 py-0.5 text-[10px] font-medium sm:inline">
          ⌘K
        </kbd>
      </Button>
      <CommandDialog open={open} onOpenChange={setOpen}>
        <CommandInput
          placeholder="Search companies, recruiters, postings…"
          value={query}
          onValueChange={setQuery}
        />
        <CommandList>
          <CommandEmpty>No results.</CommandEmpty>
          {results && results.data.length > 0 ? (
            <>
              <CommandGroup heading="Results">
                {results.data.slice(0, 6).map((item) => (
                  <CommandItem key={item.id} onSelect={() => go(detailPath(item))}>
                    <Building2 />
                    {item.name}
                  </CommandItem>
                ))}
              </CommandGroup>
              <CommandSeparator />
            </>
          ) : null}
          <CommandGroup heading="Navigate">
            <CommandItem onSelect={() => go("/search")}>
              <Search />
              Search VeriHire
            </CommandItem>
            {user ? (
              <CommandItem onSelect={() => go("/")}>
                <UserRound />
                Home
              </CommandItem>
            ) : (
              <CommandItem onSelect={() => go("/login")}>
                <LogIn />
                Log in
              </CommandItem>
            )}
            {user && (user.role === "admin" || user.role === "moderator") ? (
              <CommandItem onSelect={() => go("/admin")}>
                <LayoutDashboard />
                Admin console
              </CommandItem>
            ) : null}
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </>
  );
}
