import WatchlistsClient from "./WatchlistsClient";

export const dynamic = "force-dynamic";

export default function Page() {
  return (
    <div className="p-6">
      <WatchlistsClient />
    </div>
  );
}
