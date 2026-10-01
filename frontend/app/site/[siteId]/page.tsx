import { getSiteProcessedEvents } from "../../actions";
import SiteTimeline from "./SiteTimeline";

export default async function Page({
  params,
}: PageProps<"/site/[siteId]">) {
  const { siteId } = await params;
  const result = await getSiteProcessedEvents(siteId);

  return (
    <SiteTimeline
      siteId={siteId}
      initialEvents={result.data ?? []}
      initialLoadError={result.error !== null}
    />
  );
}
