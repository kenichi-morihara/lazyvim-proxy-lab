import { greet } from './helpers';

const message = greet('Ada');
const broken: number = 'type-error'; // Intentional diagnostic.

export function App() {
  return <main>{message}: {broken}</main>;
}
