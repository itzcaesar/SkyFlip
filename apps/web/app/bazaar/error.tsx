'use client';

export default function BazaarError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <div className="empty-state page-error"><h2>Bazaar view could not load.</h2><p>The frontend received an unexpected response. Your market data was not replaced.</p><button className="secondary-button" onClick={() => reset()}>Try again</button></div>;
}

