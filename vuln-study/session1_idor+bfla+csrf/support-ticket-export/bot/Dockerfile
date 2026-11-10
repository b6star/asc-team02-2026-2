FROM mcr.microsoft.com/playwright:v1.52.0-noble

WORKDIR /bot
COPY package.json .
RUN npm install --omit=dev
COPY bot.js .

EXPOSE 3000
CMD ["node", "bot.js"]

