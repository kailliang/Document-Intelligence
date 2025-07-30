FROM node:20-slim

WORKDIR /usr/src/app

COPY . .

RUN npm install

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]


