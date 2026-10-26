<!-- Local adaptation 2026-10-21: reduced prescriptive file splitting and architecture rules; see SOURCE.json. -->
# SwiftUI Views

- Extract a separate `View` when identity, reuse, readability, or observed update costs justify it. Small private view helpers can remain; respect the existing structure.
- Flag `body` properties that are excessively long; they should be broken into extracted subviews.
- If the user has created a handful of small, private helper `some View` properties for structural readability, and they both belong to the same concern as `body` and would fit in `body` at an acceptable length if inlined, these can be left alone. Otherwise, they should be extracted to new `View` structs.
- Button actions should be extracted from view bodies into separate methods, to avoid mixing layout and logic.
- Similarly, general business logic should not live inline in `task()`, `onAppear()` or elsewhere in `body`.
- Keep business logic testable using the project's existing boundaries. Do not introduce a view model solely because a view exists.
- Keep related small types together when that matches project conventions; split files when cohesion or navigation improves.
- Unless a full-screen editing experience is required, prefer using `TextField` with `axis: .vertical` to using `TextEditor`, because it allows placeholder text. If a specific minimum height is required for `TextField`, use something like `lineLimit(5...)`.
- If a button action can be provided directly as an `action` parameter, do so. For example: `Button("Label", systemImage: "plus", action: myAction)` is preferred over `Button("Label", systemImage: "plus") { action() }`.
- When rendering SwiftUI views to images, strongly prefer `ImageRenderer` over `UIGraphicsImageRenderer`.
- `#Preview` should be used for previews, not the legacy `PreviewProvider` protocol.
- When using `TabView(selection:)`, use a binding to a property that stores an enum rather than an integer or string. For example, `Tab("Home", systemImage: "house", value: .home)` is better than `Tab("Home", systemImage: "house", value: 0)`.
- Remove a `Group` that merely wraps one view; attach its modifiers to that view directly. For example, `Group { Image(systemName: "leaf") }` adds no visual behavior, but gives the compiler another type to check throughout the modifier chain. Groups containing siblings, a `ForEach`, or conditional branches serve a purpose and should stay, except around branches inside a `List` row, where a `VStack` is needed instead so that the row's shape does not depend on which branch ran.

Examples use the Xcode 27+ name `@ContentBuilder`, which has no minimum iOS; keep `@ViewBuilder` on earlier toolchains and leave existing uses unchanged.


## Animating views

- Strongly prefer the `@Animatable` macro: it supplies `Animatable` conformance and `animatableData` automatically. Mark properties that cannot or should not animate, such as integers and Booleans, with `@AnimatableIgnored`. Write `animatableData` manually only when its setter needs behavior the macro cannot generate, such as range limiting or normalization; use `AnimatableValues` on iOS 26+, or `AnimatablePair` for earlier targets.
- For an animated `ViewModifier`, use `@Animatable` rather than the deprecated `AnimatableModifier` protocol.
- Never use `animation(_ animation: Animation?)`; always provide a value to watch, such as `.animation(.bouncy, value: score)`.
- Chaining animations must be done using a `completion` closure passed to `withAnimation()`, rather than trying to execute multiple `withAnimation()` calls using delays.

For example:

```swift
Button("Animate Me") {
    withAnimation {
        scale = 2
    } completion: {
        withAnimation {
            scale = 1
        }
    }
}
```


## Reordering and swipe actions

The following requires iOS 27+ and is unavailable on tvOS.

- Enable drag reordering with `reorderable()` on the `ForEach` and `reorderContainer(for:)` on its enclosing container. Apply the callback's `ReorderDifference` to the source data yourself; SwiftUI does not mutate it. This works in lists, lazy stacks and grids, ordinary stacks, and custom layouts. Earlier versions require `List` with `onMove()` or a custom drag implementation. Elements must conform to `Identifiable`, or use the `itemID:` overload.

For example:

```swift
ScrollView {
    LazyVStack {
        ForEach(bookmarks) { bookmark in
            BookmarkRow(bookmark: bookmark)
        }
        .reorderable()
    }
    .reorderContainer(for: Bookmark.self) { change in
        change.apply(to: &bookmarks)
    }
}
```

SwiftUI has no built-in way to apply this difference. Add a helper like this one, adapted from an Apple example, in its own file. It inserts moved items in `sources` order, which is the order the person selected them rather than their current collection order:

```swift
extension ReorderDifference where CollectionID == ReorderableSingleCollectionIdentifier {
    func apply<Items>(to items: inout Items)
    where Items: RangeReplaceableCollection,
          Items.Element: Identifiable,
          Items.Element.ID == ItemID {
        let relocated = sources.compactMap { sourceID in
            items.first { $0.id == sourceID }
        }
        let sourceIDs = Set(sources)
        items.removeAll { sourceIDs.contains($0.id) }

        switch destination.position {
        case .before(let followingID):
            let insertionPoint = items.firstIndex { $0.id == followingID } ?? items.endIndex
            items.insert(contentsOf: relocated, at: insertionPoint)
        case .end:
            items.append(contentsOf: relocated)
        }
    }
}
```

- For moves across sections, identify each inner collection with `reorderable(collectionID:)`, and use `reorderContainer(for:in:)` on the enclosing container. Read `difference.destination.collectionID` to determine the receiving section.
- Reordering needs no drag-and-drop code; `reorderContainer(for:)` already acts as the drag container. Add `dragContainer(for:)` to the same container only when items should also take part in system drag and drop, such as dragging out to other views or apps, and make the item type `Transferable`. A `draggable()` on a row has no effect on reordering.
- Swipe actions also work in scroll views containing lazy stacks, lazy grids, or ordinary stacks. Apply `swipeActions()` to the rows and `swipeActionsContainer()` to the `ScrollView`; omitting the latter leaves the actions inactive without an error.
