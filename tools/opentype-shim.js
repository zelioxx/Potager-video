// three.js (TTFLoader) importe opentype.js depuis un CDN avec un export par défaut : on le redirige vers la copie locale.
import * as opentype from '../node_modules/opentype.js/dist/opentype.mjs';
export default opentype.default ?? opentype;
