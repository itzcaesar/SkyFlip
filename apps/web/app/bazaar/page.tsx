import { BazaarScreener } from '@/app/components/bazaar-screener';

export default async function BazaarPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  return <BazaarScreener initialParams={await searchParams} />;
}
