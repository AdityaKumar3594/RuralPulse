import type { TFunction } from 'i18next'
import type { TrainingModule } from './types'

export function priceText(t: TFunction, m: Pick<TrainingModule, 'price_type' | 'price_inr'>): string {
  if (m.price_type === 'free') return t('training.price.free')
  const kind = t(`training.price.${m.price_type}`, { defaultValue: m.price_type })
  return m.price_inr ? `${kind}: ₹${m.price_inr}` : kind
}
