import { BazaarDetail } from '@/app/components/bazaar-detail';

export default async function BazaarProductPage({ params }: { params: Promise<{ productId: string }> }) {
  const { productId } = await params;
  return <BazaarDetail productId={decodeURIComponent(productId)} />;
}

