"use client";

import type { components } from "@verihire/shared";
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ApiError } from "@/lib/api-client/client";
import { useConfirmReport, usePendingReports, useRejectReport } from "@/lib/admin/use-admin";

type ReportRead = components["schemas"]["ReportRead"];

const CATEGORY_LABELS: Record<string, string> = {
  advance_fee: "Advance fee",
  fake_job_posting: "Fake job posting",
  impersonation: "Impersonation",
  data_harvesting: "Data harvesting",
  pyramid_scheme: "Pyramid scheme",
  interview_scam: "Interview scam",
  payment_scam: "Payment scam",
  other: "Other",
};

function ActionsCell({ report }: { report: ReportRead }) {
  const [reason, setReason] = useState("");
  const [mode, setMode] = useState<"confirm" | "reject" | null>(null);
  const confirmReport = useConfirmReport();
  const rejectReport = useRejectReport();

  const submit = async () => {
    if (reason.trim().length < 5) {
      toast.error("Give a short reason (at least 5 characters).");
      return;
    }
    try {
      if (mode === "confirm") {
        await confirmReport.mutateAsync({ id: report.id, body: { reason } });
        toast.success("Report confirmed. Re-scoring the subject now.");
      } else {
        await rejectReport.mutateAsync({ id: report.id, body: { reason } });
        toast.success("Report rejected.");
      }
      setMode(null);
      setReason("");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.problem.detail : "Something went wrong.");
    }
  };

  if (mode) {
    return (
      <div className="flex flex-col gap-2">
        <textarea
          autoFocus
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Reason (required, kept in the audit log)"
          rows={2}
          className="w-56 rounded-[var(--radius-control)] border border-border bg-surface-0 px-2 py-1 text-xs"
        />
        <div className="flex gap-2">
          <Button
            size="sm"
            variant={mode === "confirm" ? "default" : "destructive"}
            onClick={() => void submit()}
            disabled={confirmReport.isPending || rejectReport.isPending}
          >
            Submit
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setMode(null)}>
            Cancel
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-2">
      <Button size="sm" onClick={() => setMode("confirm")}>
        Confirm
      </Button>
      <Button size="sm" variant="destructive" onClick={() => setMode("reject")}>
        Reject
      </Button>
    </div>
  );
}

const columns: ColumnDef<ReportRead>[] = [
  {
    accessorKey: "subject_type",
    header: "Subject",
    cell: ({ row }) => (
      <span className="capitalize">{row.original.subject_type.replace("_", " ")}</span>
    ),
  },
  {
    accessorKey: "category",
    header: "Category",
    cell: ({ row }) => CATEGORY_LABELS[row.original.category] ?? row.original.category,
  },
  {
    accessorKey: "description",
    header: "Description",
    cell: ({ row }) => (
      <p className="max-w-md truncate text-muted-foreground" title={row.original.description}>
        {row.original.description}
      </p>
    ),
  },
  {
    accessorKey: "created_at",
    header: "Filed",
    cell: ({ row }) => new Date(row.original.created_at).toLocaleDateString(),
  },
  {
    id: "actions",
    header: "Actions",
    cell: ({ row }) => <ActionsCell report={row.original} />,
  },
];

export default function AdminReportsPage() {
  const { data, isLoading, isError, refetch } = usePendingReports();

  const table = useReactTable({
    data: data?.data ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Report triage</h1>
        <p className="text-sm text-muted-foreground">
          Confirming caps the subject&apos;s Trust Score at 25 and re-scores it immediately.
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12" />
          ))}
        </div>
      ) : isError ? (
        <ErrorState message="Couldn't load reports." onRetry={() => void refetch()} />
      ) : data && data.data.length === 0 ? (
        <EmptyState title="Queue is empty" description="No pending reports right now." />
      ) : (
        <div className="rounded-[var(--radius-card)] border border-border bg-surface">
          <Table>
            <TableHeader>
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <TableHead key={header.id}>
                      {header.isPlaceholder
                        ? null
                        : flexRender(header.column.columnDef.header, header.getContext())}
                    </TableHead>
                  ))}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
