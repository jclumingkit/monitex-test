import { getProcessedEvents } from "../actions";
import DashboardContent from "../components/DashboardContent";

export default async function Page() {
  const result = await getProcessedEvents();

  return (
    <DashboardContent
      initialEvents={result.data ?? []}
      initialLoadError={result.error !== null}
    />
  );
}
