import fs from "fs-extra";
import slugify from "slugify";

interface PreviewInput {
  url_blog_crawl: string;
  blogHandle: string;
  author: string;
  content: {
    title: string;
    seo_title?: string;
    meta_desc?: string;
    html: string;
    images?: Array<{ src?: string; alt?: string }>;
  };
}

export async function writePreview(item: PreviewInput) {
  const dir = "out/review";
  await fs.ensureDir(dir);
  const slug = slugify(item.content.title || "draft", { lower: true, strict: true }).slice(0, 80) || "draft";
  const base = `${dir}/${slug}`;

  const html = `<!doctype html><meta charset="utf-8">
<title>${item.content.title}</title>
<h1>${item.content.title}</h1>
<p><strong>Blog:</strong> ${item.blogHandle}</p>
<p><strong>Author:</strong> ${item.author}</p>
<p><strong>SEO Title:</strong> ${item.content.seo_title || ""}</p>
<p><strong>Meta Desc:</strong> ${item.content.meta_desc || ""}</p>
<hr/>
${item.content.html}`;

  await fs.writeFile(`${base}.html`, html, "utf8");
  await fs.writeJSON(
    `${base}.json`,
    {
      source: item.url_blog_crawl,
      blog: item.blogHandle,
      author: item.author,
      content: item.content,
    },
    { spaces: 2 },
  );

  return { htmlPath: `${base}.html`, jsonPath: `${base}.json` };
}
