import WatchlistDetailClient from "../WatchlistDetailClient";

export const dynamic = "force-dynamic";

interface Props {
  params: { id: string };
}

export default function Page({ params }: Props) {
  return (
    <div className="p-6">
      <WatchlistDetailClient id={params.id} />
    </div>
  );
}
