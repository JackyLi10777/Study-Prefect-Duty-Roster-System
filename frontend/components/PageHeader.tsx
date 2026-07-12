export function PageHeader({
  kicker,
  title,
  children
}: {
  kicker: string;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="mb-8">
      <p className="page-kicker">{kicker}</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-normal md:text-4xl">{title}</h1>
      {children ? <p className="mt-3 max-w-3xl leading-7 text-[color:var(--muted)]">{children}</p> : null}
    </header>
  );
}

