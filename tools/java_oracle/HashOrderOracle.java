import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.HashMap;
import java.util.Map;

/**
 * Test oracle for redsim.core.javahash: replays put/remove operations on a real
 * java.util.HashMap keyed by a BlockPos-like record and prints the iteration order.
 *
 * Input lines: "put x y z" | "remove x y z" | "end" (prints keys, then starts a new map).
 */
public final class HashOrderOracle {
    record Pos(int x, int y, int z) {
        @Override
        public int hashCode() {
            return (y + z * 31) * 31 + x; // net.minecraft.core.Vec3i.hashCode
        }
    }

    public static void main(String[] args) throws Exception {
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        Map<Pos, Boolean> map = new HashMap<>();
        StringBuilder out = new StringBuilder();
        for (String line; (line = in.readLine()) != null; ) {
            String[] p = line.trim().split("\\s+");
            switch (p[0]) {
                case "put" -> map.put(new Pos(Integer.parseInt(p[1]), Integer.parseInt(p[2]), Integer.parseInt(p[3])), true);
                case "remove" -> map.remove(new Pos(Integer.parseInt(p[1]), Integer.parseInt(p[2]), Integer.parseInt(p[3])));
                case "end" -> {
                    StringBuilder row = new StringBuilder();
                    for (Pos pos : map.keySet()) {
                        row.append(pos.x()).append(',').append(pos.y()).append(',').append(pos.z()).append(';');
                    }
                    out.append(row).append('\n');
                    map = new HashMap<>();
                }
                default -> { }
            }
        }
        System.out.print(out);
    }
}
