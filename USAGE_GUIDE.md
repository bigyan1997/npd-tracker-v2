# Using NPD Tracker (simple guide)

This is an easy, step-by-step guide for using the app. No tech knowledge
needed!

## 1. Opening the app

1. **At the office:** make sure your computer or phone is on the office
   network. **From home:** open the **Tailscale** app first and make sure it
   says *Connected*.
2. Open your web browser (like Chrome).
3. Type in the address you were given.
4. That's it! You don't need to download or install anything.

## 2. Signing in

Type the **email** and **password** you were given, then click **Sign in**.
Click **Show** next to the password box if you want to check what you typed.

> Everyone at Achieve signs in with the same shared account. That's fine —
> just remember that other people may be working in the tracker at the same
> time as you (see *"Someone else changed this product"* below).

## 3. The top bar

- **Google Sheet ↗** — opens the spreadsheet copy of all products (see
  section 9).
- **Photos ↗** — opens the **NPD Tracker Photos** folder in Google Drive,
  where every product's photos are kept (see section 6).
- **Log out** — signs you out.

## 4. Looking at products

When you sign in, you'll see a big list — one row for each product. At the
top there are coloured boxes showing how many products are in each stage
(like "New Product," "Activated / Live," and so on).

- **Search** — type in the search box to find a product by its name,
  supplier, product code, or Qblue/B2B name. Part of a word is enough, and
  capitals don't matter. Under the search box you'll see how many products
  were found (e.g. **3 products found**) — click **Clear** to reset the search
  and all filters.
- **Filter** — use the dropdown boxes to only show certain statuses, only
  Active (or Inactive) products, or products that are **missing photos**.
- **Sort** — click a column title (like "Date" or "Cost") to sort the list by
  that column. Click it again to flip the order.
- **Checklist** — the small coloured boxes show the steps for getting a
  product ready to sell. Green means done, grey means not done yet. Hover
  your mouse over them to see what each one means.
- **Photos** — shows how many photos each product has:
  - `P 2 · N 1` = 2 product photos and 1 nutrition label photo.
  - A dash in orange (e.g. `N —`) means that kind of photo is still missing.
  - **No photos** (yellow) means nothing has been uploaded yet.
- **⚠ Stuck** — if a product has been sitting in the same status for a month
  or more, you'll see a little "Stuck" warning next to its status. Just a
  gentle reminder to check on it.

**The list updates by itself.** Every 20 seconds it quietly checks for
changes other people have made, so you don't need to refresh the page.

**"A new version of NPD Tracker is available"** — if you see this yellow bar
at the top, the app has been improved. Save anything you're working on, then
click **Reload**.

## 5. Adding or editing a product

1. To add one, click the orange **+ New Product** button. To edit one, click
   anywhere on its row (or the pencil ✎ icon).
2. Fill in the boxes. The ones with a little red star (*) must be filled in —
   the rest you can leave blank and fill in later.
3. For **Date** boxes: click them to open a little calendar and pick a date.
4. Click **Save Product**.

**The Supplier box:**
- Click the box to see the list of suppliers, and click one to pick it.
- **Add a new supplier:** click the **+** button next to the box, type the
  name, and click **Add**.
- **Rename a supplier:** open the list and click the **pencil ✏️** next to the
  supplier. Change the name and click **Save** — every product using that
  supplier is updated too.
- **Delete a supplier:** click the **bin** icon next to it in the list. (You
  can't delete a supplier that's still used by a product.)
- Once you've picked a supplier, the box locks so you don't change it by
  accident — click the little **×** to clear it.

**History:** when editing, click **History** at the top to see everything
that's ever changed on that product and when. Click **Edit** to go back.

**"This product was changed by someone else while you had it open"** — this
means someone else saved the same product after you opened it. Your changes
have *not* been saved yet. You can:
- **Load latest version** — see their changes (you'll need to type yours
  again), or
- **Save mine anyway** — keep your version (this replaces their changes).

## 6. Photos

Every product has two kinds of photos:
- **Product Photos** — regular pictures of the product.
- **Nutrition Label Photos** — pictures of the nutrition label.

**In the app:** scroll down to **Photos** in the product form.
- Click **+ Add** to upload photos from your computer or phone. You can add
  them while creating a new product too — they're uploaded when you save.
- Click a photo to see it full size.
- Hover over a photo and click the **✕** to delete it. The app will warn you
  that it's deleted from Google Drive too.

**In Google Drive:** all photos are kept in the **NPD Tracker Photos** folder
in the achievecafeprovisions Google Drive. Each product has its own folder
with **Product photos** and **Nutrition labels** inside.
- You can add, move, rename or delete photos right there — for example from
  the Google Drive app on your phone. The tracker catches up within about 2
  minutes (straight away when you open that product).
- The **Open in Google Drive ↗** link in the product form goes straight to
  that product's folder.

**Deleted a photo by mistake?** Open Google Drive, go to **Bin**, and restore
it — deleted photos stay there for 30 days.

## 7. Deleting a product (and undoing it!)

1. Click the trash icon 🗑 next to a product (or the **Delete** button inside
   the edit screen).
2. It will ask you to confirm — click **Delete**. The product's photo folder
   goes to the Google Drive Bin too.

**Made a mistake?** Click the **Recently Deleted** button at the top of the
page and click **Restore** next to the product. Its details come back, but
its photos don't come back automatically — restore the folder from the
Google Drive Bin (within 30 days) and move the photos into the product's new
folder.

## 8. Importing and exporting

- **Export CSV** — downloads the whole list as a file you can open in Excel.
  (If a date column shows `#####` in Excel, just make the column wider.)
- **Import CSV** — lets you add lots of products at once from a file. Click
  it, choose your file, and the app will show you a preview first — so you
  can check everything looks right before anything is actually saved. Tip:
  click **Export CSV** first to get a file with the exact right columns.

## 9. The Google Sheet

The **Google Sheet ↗** button opens a spreadsheet copy of every product that
updates itself whenever something changes in the tracker.

- **Only make changes in the tracker, not in the sheet.** The sheet is just a
  copy — anything typed into it gets overwritten.
- **Search tab** (the first tab) — type anything in the **yellow box** and
  every matching product is listed underneath, with a count.
- **NPD tab** — every column heading has a **▼** filter button, like Excel.
  Because everyone shares the sheet, please remove your filter when you're
  done (**Data → Remove filter**).
- The **Photograph & Save Images** column has an **Open photos folder** link
  for each product.

## If something doesn't work

- **Can't open the page at all** — make sure you're on the office network
  (or Tailscale says *Connected* if you're at home), and that the office
  computer running the app is turned on.
- **Something looks out of date** — press **F5** to reload the page.
- **"Couldn't reach Google Drive"** — the internet or Google is having a
  moment. Wait a minute and try again.
- **Still stuck?** — ask whoever manages the app for this team for help.
