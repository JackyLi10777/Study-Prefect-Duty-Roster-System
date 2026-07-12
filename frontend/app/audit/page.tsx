import { PageHeader } from "@/components/PageHeader";

export default function AuditPage() {
  return (
    <div>
      <PageHeader kicker="Fairness Audit / 公平審核" title="Responsibility, Not Privilege">
        Fairness audit will make duty load and history weight visible so leadership remains accountable and equitable.
      </PageHeader>
      <section className="rounded-lg border border-[color:var(--line)] bg-white/70 p-6 dark:bg-white/5">
        <h2 className="font-semibold">Audit model pending</h2>
        <p className="mt-2 leading-7 text-[color:var(--muted)]">
          The domain scaffold already calculates duty weights. The next step is to persist roster history and expose cumulative load by prefect.
        </p>
      </section>
    </div>
  );
}

