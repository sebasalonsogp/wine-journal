export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-6 py-12">
      <p className="text-sm font-medium tracking-wide text-secondary">Wine Journal</p>
      <h1 className="mt-4 font-serif text-4xl leading-tight text-primary sm:text-5xl">
        Remember the wine.
        <br />
        Keep the moment.
      </h1>
      <p className="mt-6 max-w-md text-lg text-foreground">
        A place for the bottles you discover, the notes you make, and the memories you share.
      </p>
      <p className="mt-8 text-sm text-muted-foreground">
        The journal is taking shape. Coming soon.
      </p>
    </main>
  );
}
