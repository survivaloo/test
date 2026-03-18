interface Props {
  title: string;
  icon: string;
}

export function ComingSoon({ title, icon }: Props) {
  return (
    <section className="px-4 pb-24 flex flex-col items-center justify-center min-h-[50vh]">
      <span className="text-6xl mb-4">{icon}</span>
      <h2 className="text-lg font-bold mb-2">{title}</h2>
      <p className="text-gray-500 dark:text-gray-400 text-center">
        Phase 2で実装予定です
      </p>
    </section>
  );
}
