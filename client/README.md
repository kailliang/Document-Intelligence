# Patent Reviewer UI

## Layout

Application code is in the `src/` directory. Everything under `src/internal/` should not be modified, but feel free to take a look at the internals - think of it as a third party library.

```
src
├── App.tsx # Main App Shell
├── Document.tsx # Document with WebSocket link
├── internal
│   ├── Editor.tsx # React Quill Editor
├── main.tsx
```

## Running locally

To run locally,

```sh
npm install
npm run dev
```
