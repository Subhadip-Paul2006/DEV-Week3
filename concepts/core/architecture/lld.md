---
id: foundation.lld
category: foundation
owning_agent: F-03
maturity: stable
languages:
- any
tags:
- solid
- coupling
- cohesion
- design-patterns
- oop
- clean-code
- single-responsibility
- dependency-inversion
related:
- foundation.hld
- foundation.circuit-breaker
- foundation.connection-pooling
- foundation.error-handling
- foundation.client-server
domain: core
---

# Low-Level Design (LLD)

## 1. Overview

Low-Level Design (LLD) is the discipline of organizing code inside a single component (a service, library, or module) so that it is easy to read, change, test, and hard to break. Where HLD decides *which boxes exist and how they talk*, LLD decides *what each box looks like on the inside* — class structure, function signatures, module boundaries, dependency direction, error handling, and the patterns that turn a tangled script into software that can be maintained for a decade. LLD draws on principles like SOLID, GRASP, the Law of Demeter, the four rules of simple design, and a working knowledge of the GoF design patterns. It is the discipline that determines whether a codebase rots into a "big ball of mud" or stays navigable as the team and feature surface grow.

## 2. Core Principles

1. **One reason to change** — every module, class, and function has one axis along which it changes; two reasons means two responsibilities, which means split.
2. **High cohesion, low coupling** — the things that change together stay together; the things that change independently stay apart.
3. **Depend on abstractions, not concretions** — code should not be bound to a specific implementation; swapping Postgres for MySQL should change one place.
4. **Make the easy thing to do the right thing** — code structure, naming, and defaults should guide engineers toward correct usage; the wrong thing should be hard.
5. **No global mutable state** — globals are shared mutable state by another name; they make testing impossible and concurrency unsafe.
6. **Fail fast and loud** — invalid state should be detected at the boundary where it enters the system, not 30 function calls later.
7. **Testability is a design property** — if a function can't be unit tested without spinning up a database, the design is wrong; inject the dependency.

## 3. Sub-Concepts

### 3.1 SOLID Principles

**Definition:** Five principles articulated by Robert C. Martin that produce code open to extension, closed to modification, substitutable, narrowly scoped, and decoupled from its dependencies.

#### S — Single Responsibility Principle (SRP)

A class or module has one, and only one, reason to change.

```python
# WRONG: User class handles persistence, validation, email, AND reporting
class User:
    def save_to_db(self): ...
    def validate_email(self): ...
    def send_welcome_email(self): ...
    def generate_report(self): ...

# CORRECT: split responsibilities
class User:                       # data + behavior
    def __init__(self, email, name): ...
class UserRepository:             # persistence
    def save(self, user): ...
class UserValidator:              # validation
    def validate(self, user): ...
class WelcomeEmailSender:         # notification
    def send(self, user): ...
```

#### O — Open/Closed Principle (OCP)

Open for extension, closed for modification. New behavior is added by writing new code, not by editing existing, tested code.

```typescript
// WRONG: adding a new discount type means editing this function
function applyDiscount(order: Order, type: string): Order {
    if (type === "percentage") { /* ... */ }
    else if (type === "fixed")   { /* ... */ }
    else if (type === "buy2get1"){ /* ... */ }   // edit forever
}

// CORRECT: DiscountStrategy interface
interface DiscountStrategy { apply(order: Order): Order; }
class PercentageDiscount implements DiscountStrategy { /* ... */ }
class FixedDiscount implements DiscountStrategy       { /* ... */ }
class OrderProcessor {
    constructor(private discount: DiscountStrategy) {}
    process(order: Order): Order { return this.discount.apply(order); }
}
```

#### L — Liskov Substitution Principle (LSP)

Subtypes must be substitutable for their base types. A `Square` that extends `Rectangle` and breaks when width is set independently violates LSP. Fix: do not model Square as a subtype of Rectangle; use a common `Shape` interface or composition.

#### I — Interface Segregation Principle (ISP)

Clients should not be forced to depend on methods they do not use.

```go
// WRONG
type Animal interface { Fly() error; Swim() error; Bark() error }
type Dog struct{}
func (Dog) Fly() error { return errors.New("dogs don't fly") }   // forced

// CORRECT
type Mover interface { Move() error }
type Swimmer interface { Swim() error }
```

#### D — Dependency Inversion Principle (DIP)

High-level modules should not depend on low-level modules; both depend on abstractions.

```python
# WRONG
from myapp.db.postgres import PostgresOrderRepo
class OrderService:
    def __init__(self):
        self.repo = PostgresOrderRepo()

# CORRECT
from typing import Protocol
class OrderRepository(Protocol):
    def save(self, order: Order) -> None: ...
    def find(self, id: str) -> Order: ...
class OrderService:
    def __init__(self, repo: OrderRepository):
        self.repo = repo
```

**Common mistakes:** Confusing SRP with "one method per class"; treating SOLID dogmatically; confusing OCP with "no edits ever" — bugs in existing code require edits.

**Scanner signals:** Presence of `interface`/`Protocol`/abstract class; constructor dependency injection. Negative: classes named `Manager`/`Helper`/`Utils`/`Handler` with > 10 public methods.

### 3.2 Coupling and Cohesion

**Definition:** Two axes of code quality, originally articulated by Larry Constantine. **Coupling** = how much one module knows about another. **Cohesion** = how strongly the responsibilities of a single module belong together.

**Coupling types (worst → best):** content (shared mutable globals), common (shared global var), control (flag passed to control logic), stamp (data structure passed but only part used), data (parameters only).

**Cohesion types (worst → best):** coincidental ("misc", "utils"), logical (read_file, write_file), temporal (init/cleanup), procedural (must run in order), communicational (operates on same data), sequential (output feeds next), functional (single well-defined task).

**Implementation patterns:** Package by feature, not by layer; mark internal packages `internal/` (Go) or `_` (Python); use narrow interfaces (ISP).

**Scanner signals:** Positive: small public API per package. Negative: imports from `module_a.internal.*` in `module_b`; large `utils.py` files; circular imports.

### 3.3 Design Patterns (GoF + Beyond)

**Definition:** Named, reusable solutions to recurring problems. The "Gang of Four" book formalized 23 OO patterns; modern practice extends to functional and distributed.

**Creational:** Factory Method, Abstract Factory, Prototype, Builder, Singleton (use sparingly).
**Structural:** Adapter, Decorator, Facade, Proxy, Composite, Bridge, Flyweight.
**Behavioral:** Strategy, Template Method, Command, State, Chain of Responsibility, Mediator, Memento, Visitor, Observer.

**Modern patterns:** Repository, Unit of Work, Specification, Pub/Sub, CQRS, Saga, Outbox, Bulkhead, Sidecar, Strangler Fig.

**Anti-patterns to recognize:** Golden Hammer (one pattern for everything); Inner Platform Effect (reimplementing a framework); Anemic Domain Model (data without behavior).

**Scanner signals:** Presence of named factories (`*Factory`), repositories (`*Repository`), strategies (`*Strategy`).

### 3.4 Module / Package Structure

**Definition:** How code is organized into files, packages, and modules. Determines import direction and how easy it is to navigate the codebase.

**Implementation patterns:**

- **Package by feature** — `orders/`, `users/`, `inventory/` each contain their own domain, persistence, tests. Inside: high cohesion; across: low coupling.
- **Package by layer** — `controllers/`, `services/`, `repositories/`. Easier to enforce layers, lower cohesion.
- **Hexagonal (Ports & Adapters)** — `domain/` (pure), `ports/` (interfaces), `adapters/` (concrete). Dependencies point inward toward `domain/`.
- **Clean Architecture** — entities → use cases → interface adapters → frameworks. Uncle Bob's Hexagonal variant.

**Common mistakes:** Cyclic imports, leaky abstractions (`*sql.Row` exposed through a service interface), mixed layers (`models/` containing both domain entities and ORM models).

**Scanner signals:** `internal/` directories (Go); curated `__init__.py`. Negative: cyclic import graph; `from myapp.orders.models import *` from inside `users/`.

### 3.5 Error Handling

**Definition:** How the code detects, communicates, and recovers from error conditions.

**Patterns:** Exceptions (Python/Java/C#), Result types (`Result<T,E>`, Rust/Go), error codes (C), panic/fail-fast (unrecoverable programmer errors).

**Principles:** Fail at the boundary; include context (request ID, input, operation); never swallow (`except: pass` is a bug); translate at the boundary (low-level `psycopg2.OperationalError` → high-level `InventoryUnavailable`); log once (don't log and rethrow).

```python
# WRONG
try: process_payment(order)
except Exception: pass

# WRONG
try: user = repo.find(user_id); logger.error("user not found"); raise

# CORRECT
class OrderError(Exception): pass
def place_order(order):
    try: repo.save(order)
    except UniqueViolation as e:
        raise OrderError(f"duplicate order {order.id}") from e
    except DBConnectionError as e:
        raise OrderError("inventory unavailable") from e
```

**Scanner signals:** Typed exception hierarchy; narrow `try` blocks; `raise X from Y` for context. Negative: bare `except:`; `print()` for error reporting.

### 3.6 Immutability and Value Objects

**Definition:** Objects that cannot be modified after creation. Value objects are defined by their attributes, not by an identity (`Money`, `Date`, `Coordinate`).

```python
# CORRECT in Python
from dataclasses import dataclass
@dataclass(frozen=True)
class Money:
    amount: int       # cents
    currency: str
    def __post_init__(self):
        if self.amount < 0: raise ValueError("amount must be >= 0")
    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("currency mismatch")
        return Money(self.amount + other.amount, self.currency)

# WRONG: mutating a passed-in object
def apply_discount(order, percentage):
    order.total *= (1 - percentage)

# CORRECT
def apply_discount(order: Order, percentage: float) -> Order:
    return Order(items=order.items, total=order.total * (1 - percentage))
```

**Scanner signals:** `@dataclass(frozen=True)` (Python), `final` (Java), `readonly` (TypeScript).

### 3.7 Dependency Injection and Composition Root

**Definition:** A component receives its dependencies from outside. The composition root (`main`) wires the dependency graph.

```python
# WRONG
class OrderService:
    def __init__(self):
        self.repo = PostgresOrderRepo()
        self.publisher = KafkaPublisher()

# CORRECT
class OrderService:
    def __init__(self, repo: OrderRepository, publisher: EventPublisher):
        self.repo = repo; self.publisher = publisher

def main():
    db = PostgresOrderRepo(os.environ["DATABASE_URL"])
    publisher = KafkaPublisher(os.environ["KAFKA_BROKERS"])
    service = OrderService(db, publisher)
```

**Scanner signals:** Constructors with interface parameters; `main.py`/`bootstrap.ts`/`cmd/main.go` wires deps. Negative: `new SomeService()` inside business logic; `ServiceRegistry.get()` in business code.

### 3.8 Defensive Programming and Validation

**Definition:** Code that checks inputs and invariants rather than assuming callers are well-behaved.

**Patterns:** Input validation at the boundary; preconditions (`require(x > 0)`); postconditions; type-driven validation (`UserId` UUID instead of `string`; `NonEmptyList<T>` instead of `List<T>`).

```go
// CORRECT: typed IDs
type UserID string
func NewUserID(s string) (UserID, error) {
    if _, err := uuid.Parse(s); err != nil {
        return "", fmt.Errorf("invalid user id: %w", err)
    }
    return UserID(s), nil
}
```

**Scanner signals:** `pydantic`/`zod`/`io-ts`/`class-validator` at API boundaries; type-level IDs. Negative: `string` for IDs/emails/URLs; SQL from string concatenation.

### 3.9 Testability as a Design Constraint

**Definition:** Code designed so units can be tested in isolation — without a real database, network, or filesystem.

```python
# WRONG: untestable
def is_business_day(date):
    today = datetime.now()
    return today.weekday() < 5

# CORRECT: clock injected
def is_business_day(date, clock: Callable[[], datetime]):
    return clock().weekday() < 5
```

**Scanner signals:** High unit test coverage; `mocks/`/`fakes/`/`test_doubles/` directories. Negative: `time.sleep()` in business logic; reading env vars inside business functions.

## 4. Scanner Signals

### 4.1 Presence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Interface / Protocol / abstract base class | Python/TS/Go | regex: `class.*Protocol\|interface \|^type.*interface` | High |
| Constructor dependency injection | Python/TS/Go | AST: constructor params assigned to fields | High |
| Frozen dataclass / final / readonly modifier | Python/TS/Go/Java | regex: `@dataclass\(frozen=True\)\|final \|readonly \|const ` | High |
| Composition root (single wiring location) | any | filename: `main.py`, `bootstrap.ts`, `app.module.ts`, `cmd/main.go` with `wire\|build` calls | Medium |
| Domain layer with no external imports | Python/TS/Go | regex: `from myapp.adapters\|import myapp.infrastructure` inside `domain/` | High |
| Repository / DAO abstraction | Python/TS/Go | regex: `class.*Repository\|class.*DAO\|interface.*Repository` | High |
| Strategy: interface + multiple implementations | Python/TS/Go | regex: `implements.*Strategy\|*Strategy =` | Medium |
| Factory function/method | Python/TS/Go | regex: `def make_\|@classmethod\s*\n\s*def create` | Medium |
| Type-safe IDs (UserId vs raw strings) | any | regex: `type UserId\|type OrderId\|class UserId` | Medium |
| Validation at API boundary | Python/TS | regex: `pydantic\|zod\|io-ts\|class-validator` | High |
| Test doubles / mocks present | any | glob: `**/mocks/**`, regex: `MagicMock\|jest.mock\|testify/mock` | Medium |
| Unit tests with high coverage | any | glob: `**/test_*.py`, `**/*.test.ts` count > 30% of source files | Low |

### 4.2 Absence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| No interfaces in a multi-service codebase | Python/TS/Go/Java | regex: no `interface\|Protocol\|abstract` found | Medium |
| No unit tests directory | any | glob: absence of `**/test/**`, `**/*_test.go` | High |
| No composition root / no DI | any | absence of constructor parameters | Medium |
| No validation library at API boundary | Python/TS | absence of `pydantic\|marshmallow\|zod\|joi` in deps | Medium |
| No repository abstraction (services hit DB directly) | any | regex: `SELECT\|INSERT\|UPDATE` inside service classes | High |
| Singleton pattern used everywhere | any | regex: `__new__\|getInstance\|static.*instance` | Medium |

### 4.3 Misconfiguration Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Empty `except` block | Python | regex: `except\s*:?\s*\n\s*pass` | High |
| Bare `except:` clause | Python | regex: `except:\s*\n` | High |
| Catching `Exception` and rethrowing without `from` | Python | regex: `except\s+Exception\s+as\s+\w+:\s*\n\s*raise$` | Medium |
| Mutable default argument | Python | regex: `def\s+\w+\([^)]*=\s*\[\]\|def\s+\w+\([^)]*=\s*\{\}` | High |
| God class (> 500 lines, > 10 public methods) | any | AST: class > 500 LOC or > 10 public methods | High |
| Circular imports | Python/Go/TS | AST: import graph contains cycle | High |
| Print statement for error reporting | Python | regex: `print\(.*[Ee]rror\|print\(.*[Ff]ail` | Medium |
| String concatenation for SQL | any | regex: `f"SELECT.*\{` or `+ "SELECT"` | High |
| Public mutable field on a class | Python/TS/Java | AST: class field assigned in `__init__` without property | Medium |
| No timeout on external calls | any | regex: `requests.\|fetch(\|client.Do(` without timeout | High |
| Business logic reading env vars directly | any | regex: `os.environ\|process.env` in service/domain classes | Medium |
| Thread.sleep in business logic | any | regex: `time.sleep\|Thread.sleep` outside test files | High |
| Global mutable singleton with public setter | any | regex: `^_\w+\s*=\s*None` module-level + setter | High |

## 5. Anti-Patterns

#### Anti-Pattern: God Object / God Class

**Description:**
```python
class UserManager:                                  # 1,200 lines
    def create_user(...): ...
    def delete_user(...): ...
    def send_email(...): ...
    def generate_report(...): ...
    def process_payment(...): ...
    def validate_address(...): ...
    # ... 30 more methods
```

**Why it's dangerous:** Every change touches this class. Tests require mocking half the world. New engineers are afraid to modify it.

**Detection:** Class > 500 lines, > 10 public methods, or > 5 dependencies. Names ending in `Manager`/`Helper`/`Utils`/`Service`.

**Fix:** Apply SRP — split into `UserRepository`, `UserEmailer`, `UserValidator`.

#### Anti-Pattern: Anemic Domain Model

**Description:**
```java
public class Order {
    private Long id;
    private List<OrderItem> items;
    private OrderStatus status;
    // getters and setters only
}
public class OrderService {
    public void cancel(Order order) {
        if (order.getStatus() == OrderStatus.PAID) {
            order.setStatus(OrderStatus.CANCELLED);
        }
    }
}
```

**Why it's dangerous:** Logic is scattered; the `Order` object can't enforce invariants; logic is duplicated; testing requires constructing the whole world.

**Detection:** Entities with only getters/setters; all logic in services taking the entity as a parameter.

**Fix:** Move behavior onto the entity (`order.cancel()` enforces invariants internally).

#### Anti-Pattern: Empty Catch Block

**Description:**
```python
try:
    parse_user_input(raw_data)
except ValueError:
    pass    # "I don't want to deal with this"
```

**Why it's dangerous:** The error is swallowed. The program continues with invalid state. Sometimes it crashes later with a confusing error.

**Detection:** Regex `except.*:\s*\n\s*pass` or empty except blocks.

**Fix:**
```python
try:
    parse_user_input(raw_data)
except ValueError as e:
    logger.warning("invalid user input", extra={"raw": raw_data, "error": str(e)})
    return BadRequest("invalid input")
```

#### Anti-Pattern: Primitive Obsession

**Description:**
```python
# WRONG: everything is a string
def create_order(user_id: str, sku: str, quantity: str, price: str) -> None: ...
```

**Why it's dangerous:** Type system is bypassed; validations scattered; IDs collide (user_id and order_id both strings).

**Fix:** Introduce value types.
```python
@dataclass(frozen=True)
class SKU:
    value: str
    def __post_init__(self):
        if not re.match(r"^[A-Z]{3}-\d{4}$", self.value):
            raise ValueError(f"invalid SKU format: {self.value}")

@dataclass(frozen=True)
class Money:
    cents: int
    currency: str

def create_order(user_id: UserID, sku: SKU, quantity: Quantity, price: Money): ...
```

#### Anti-Pattern: Service Locator (Anti-Pattern of DI)

**Description:**
```python
class OrderService:
    def cancel(self, order_id):
        repo = ServiceRegistry.get("OrderRepository")   # hidden coupling
        publisher = ServiceRegistry.get("EventPublisher")
```

**Why it's dangerous:** Dependency is invisible at the class signature. The unit test must populate the registry. The dependency graph can't be statically analyzed.

**Detection:** `ServiceRegistry.get\|GlobalRegistry.get\|Container.resolve` inside business logic.

**Fix:** Constructor injection — the dependency appears in the signature and can be mocked.

#### Anti-Pattern: Long Parameter List

**Description:**
```typescript
function createOrder(
    userId: string, customerName: string, customerEmail: string,
    shippingStreet: string, shippingCity: string, shippingZip: string, shippingCountry: string,
    billingStreet: string, billingCity: string, billingZip: string, billingCountry: string,
    items: OrderItem[], discountCode: string, giftMessage: string
): Order
```

**Why it's dangerous:** Callers can't remember order; optional params ambiguous; adding a field breaks every caller.

**Detection:** Functions with > 5 parameters.

**Fix:** Introduce parameter objects.
```typescript
interface Address { street: string; city: string; zip: string; country: string; }
interface Customer { id: string; name: string; email: string; }
function createOrder(
    customer: Customer, shipping: Address, billing: Address,
    items: OrderItem[], options?: { discountCode?: string; giftMessage?: string }
): Order
```

#### Anti-Pattern: Mutable Default Argument (Python-specific)

**Description:**
```python
def add_item(item, cart=[]):           # BUG: cart is shared across calls
    cart.append(item)
    return cart
add_item("apple")   # ["apple"]
add_item("banana")  # ["apple", "banana"]   -- leaked state!
```

**Why it's dangerous:** Default is evaluated *once* at definition time. List shared across all calls.

**Detection:** Regex `def\s+\w+\([^)]*=\s*\[\]\|def\s+\w+\([^)]*=\s*\{\}`.

**Fix:**
```python
def add_item(item, cart=None):
    if cart is None: cart = []
    cart.append(item)
    return cart
```

## 6. Configuration Reference

| Parameter | Type | Default | Recommended | Description |
|-----------|------|---------|-------------|-------------|
| `test_coverage.threshold.lines` | float | 0 | 0.80 | Minimum line coverage for unit tests |
| `test_coverage.threshold.branches` | float | 0 | 0.70 | Minimum branch coverage |
| `linter.max_function_length_lines` | int | varies | 30 | Maximum lines per function (pylint, ESLint) |
| `linter.max_class_length_lines` | int | varies | 300 | Maximum lines per class |
| `linter.max_parameters` | int | varies | 5 | Maximum parameters per function |
| `linter.max_cyclomatic_complexity` | int | varies | 10 | Maximum cyclomatic complexity per function |
| `linter.banned_imports` | list | [] | `[datetime.now]` (in domain), `[random.random]` (in domain) | Imports forbidden in certain layers |
| `linter.banned_constructs` | list | [] | `[eval, exec, bare except, mutable default arg]` | Constructs disallowed by lint rules |
| `arch_test.allowed_dependencies` | object | {} | per-layer rules (e.g., `domain` may not import `adapters`) | Architectural rules enforced by tests (e.g., `arch_unit`) |
| `di.container.scope` | string | "singleton" | "transient" (stateful), "scoped" (request) | Default lifetime of injected dependencies |
| `error_handler.notify_on_unhandled` | bool | false | true | Send unhandled exceptions to error tracker (Sentry) |

## 7. Integration Points

- **HLD** — LLD implements the contracts defined by HLD. A service whose LLD doesn't match its HLD is a violation (e.g., HLD says "stateless" but LLD uses in-memory sticky sessions).
- **Circuit Breaker** — service methods are typically wrapped by a circuit breaker at the LLD level (decorator pattern). The breaker's interface is a design decision.
- **Connection Pooling** — repositories (LLD) wrap connection pools. Pool configuration belongs to LLD; pool implementation belongs to infra.
- **Error Handling** — error types defined in domain (LLD) get translated at infrastructure boundaries (HLD).
- **Testing** — DI (LLD) is the prerequisite for unit testing (cross-cutting concern).

## 8. Observability

| Metric | Tool | Threshold | Action |
|--------|------|-----------|--------|
| Unit test coverage | coverage.py, jest, go test -cover | < 70% → warn, < 50% → page | Add tests for uncovered branches |
| Cyclomatic complexity per function | radon, ESLint, gocyclo | > 15 → warn | Refactor |
| Class size (LOC) | pylint, SonarQube | > 500 → warn | Split (SRP) |
| Lint violations per file | eslint, ruff, golangci-lint | > 10 → warn | Fix or suppress with justification |
| Build time | CI | > 10m → warn | Parallelize; cache; split repo |
| Static analysis findings | SonarQube, CodeQL | new "blocker" → fail build | Block PR |
| Test flakiness rate | CI dashboards | > 2% → warn | Quarantine flaky tests |
| Architectural rule violations | arch-unit, dependency-cruiser | any → fail build | Block PR |

## 9. Evolution / Version Tracking

**1980s–1990s — Structured programming:** Dijkstra, Parnas, Constantine lay the foundations. Structured programming (no `goto`), top-down decomposition, and the coupling/cohesion vocabulary emerge.

**1990s — OOP boom:** The Gang of Four book (1994) formalizes 23 design patterns. Java and C++ become dominant. Inheritance is overused (the "inheritance tax") and composition is rediscovered.

**2000s — Agile + TDD:** XP, TDD, and CI make testability a first-class design property. Mocking frameworks (JUnit + Mockito, Moq, RSpec) become standard. DI containers (Spring) become mainstream.

**2010s — SOLID mainstreamed:** Robert Martin's *Clean Code* (2008) and *Clean Architecture* (2017) bring SOLID and the Dependency Rule to a generation. Hexagonal (Alistair Cockburn, 2005) and Onion Architecture gain adoption. Functional ideas (immutability, pure functions) start to influence OOP codebases.

**2020s — Pragmatism and functional influence:** Domain modeling shifts toward value objects and algebraic data types (Rust, F#, TypeScript discriminated unions). Many patterns absorbed into language features (`async/await` replaces Callback, decorators first-class in Python). Type-driven design (types as documentation) gains traction.

**Emerging patterns:** Hexagonal/Ports-and-Adapters; Functional core, imperative shell (Gary Bernhardt); Type-driven design (Rust, TypeScript strict mode); Component-based UI (React, Vue, Svelte).

**Deprecated patterns:** Singleton (replaced by DI containers and `main`-wired deps); Anemic domain model (replaced by rich domain models); Inheritance for code reuse (replaced by composition); Manual `new` everywhere (replaced by DI / factories).

## 10. References

- [Clean Code — Robert C. Martin (O'Reilly)](https://www.oreilly.com/library/view/clean-code-a/9780136083238/)
- [Clean Architecture — Robert C. Martin](https://www.oreilly.com/library/view/clean-architecture-a/9780134494166/)
- [Design Patterns: Elements of Reusable Object-Oriented Software — GoF](https://en.wikipedia.org/wiki/Design_Patterns)
- [Refactoring — Martin Fowler](https://martinfowler.com/books/refactoring.html)
- [Domain-Driven Design — Eric Evans](https://domainlanguage.com/ddd/)
- [Hexagonal Architecture — Alistair Cockburn](https://alistair.cockburn.us/hexagonal-architecture/)
- [The Pragmatic Programmer — Hunt & Thomas](https://pragprog.com/titles/tpp20/the-pragmatic-programmer-20th-anniversary-edition/)
- [Martin Fowler's Blog](https://martinfowler.com/)
- [Refactoring Guru — Design Patterns](https://refactoring.guru/design-patterns)
- [Architecture Patterns with Python (Cosmic Python)](https://www.cosmicpython.com/)
- [Effective Java — Joshua Bloch](https://www.oreilly.com/library/view/effective-java/9780134685991/)