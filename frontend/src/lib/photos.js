// Photo counts per category for a product row (rows from the products list
// already include their `images`).
export function photoCounts(row) {
  const images = row?.images ?? []
  return {
    product: images.filter((img) => img.category === 'product').length,
    nutrition: images.filter((img) => img.category === 'nutrition').length,
  }
}

export const PHOTO_FILTERS = {
  missing: (c) => c.product === 0 || c.nutrition === 0,
  'no-product': (c) => c.product === 0,
  'no-nutrition': (c) => c.nutrition === 0,
}
