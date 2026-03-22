import { getRequestConfig } from "next-intl/server";

export default getRequestConfig(async ({ requestLocale }) => {
  const locale = (await requestLocale) || "ar";

  return {
    locale,
    messages: (await import(`./messages/${locale}.json`)).default,
  };
});
