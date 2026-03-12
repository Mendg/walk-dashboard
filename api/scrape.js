// Vercel serverless function: proxies Rallybound walker data to avoid CORS
// GET /api/scrape → returns JSON array of {name, amount, url}

export default async function handler(req, res) {
  const SITE = "https://www.walk4friendship.com";
  const body = "splitFirstAndLast=true&containerId=widget-c458d5ce-e8ed-4557-a387-e50896f929f4";

  try {
    const response = await fetch(`${SITE}/Member/MemberList`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Walk4Friendship-Dashboard/1.0",
      },
      body,
    });

    const data = await response.json();

    if (!data.success) {
      res.status(502).json({ error: "Rallybound API returned success=false" });
      return;
    }

    const html = data.html;
    const rows = html.split("tableRow ajaxTableRow");
    const members = [];

    for (let i = 1; i < rows.length; i++) {
      const row = rows[i];
      const fn = row.match(/tableColSortFirstName[^>]*><a[^>]*>([^<]+)<\/a>/);
      const ln = row.match(/tableColSortLastName[^>]*><a[^>]*>([^<]+)<\/a>/);
      const amt = row.match(/data-sort="([\d.]+)"/);
      const slug = row.match(/data-href="\/([^"]+)"/);

      if (fn && ln && amt) {
        members.push({
          name: `${fn[1]} ${ln[1]}`.trim(),
          amount: parseFloat(amt[1]),
          url: slug ? `${SITE}/${slug[1]}` : "",
        });
      }
    }

    res.setHeader("Cache-Control", "s-maxage=300, stale-while-revalidate=600");
    res.status(200).json({
      fundraisers: members,
      total: members.reduce((sum, m) => sum + m.amount, 0),
      count: members.length,
      scraped_at: new Date().toISOString(),
    });
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
}
