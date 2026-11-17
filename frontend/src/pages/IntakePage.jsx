import { useState } from 'react'

import Field from '../components/Field.jsx'

// SCRUM-9 mockup: the screen a field lead fills in on site.
// Nothing is saved yet. Field names follow docs/DATA_MODEL.md (customers, projects, areas, scope_items)
// so the form can be connected to the API later without renaming anything.
// TODO(SCRUM-26): replace hard-coded text with i18n keys.

// Numbered section with a black rule on top: no cards, no shadows.
function Section({ number, title, children }) {
  return (
    <section className="border-t border-ink pt-6">
      <h2 className="mb-8 flex items-baseline gap-4 text-xs font-bold tracking-[0.25em] uppercase">
        <span className="text-gray-400">{number}</span>
        {title}
      </h2>
      {children}
    </section>
  )
}

const emptyScopeItem = () => ({
  description: '',
  prep: '',
  products: '',
  color: '',
  sheen: '',
  dimensions: '',
  included: true,
})

export default function IntakePage() {
  // Each area holds its own list of scope items.
  const [areas, setAreas] = useState([{ name: '', scope_items: [emptyScopeItem()] }])

  const addArea = () => setAreas([...areas, { name: '', scope_items: [emptyScopeItem()] }])

  const removeArea = (areaIndex) => setAreas(areas.filter((_, i) => i !== areaIndex))

  const addScopeItem = (areaIndex) =>
    setAreas(
      areas.map((area, i) =>
        i === areaIndex ? { ...area, scope_items: [...area.scope_items, emptyScopeItem()] } : area,
      ),
    )

  return (
    <form className="flex flex-col gap-16" onSubmit={(e) => e.preventDefault()}>
      <header>
        <h1 className="text-4xl font-light tracking-tight sm:text-5xl">New job intake</h1>
        <p className="mt-3 text-sm text-gray-500">Capture the site, the rooms and the finish.</p>
      </header>

      <Section number="01" title="Customer">
        {/* One column on phones, two from the sm breakpoint (640px) up */}
        <div className="grid gap-x-8 gap-y-8 sm:grid-cols-2">
          <Field label="Customer name" name="name" className="sm:col-span-2" />
          <Field label="Phone" name="phone" type="tel" />
          <Field label="Email" name="email" type="email" />
        </div>
      </Section>

      <Section number="02" title="Job site">
        <div className="grid gap-x-8 gap-y-8 sm:grid-cols-2">
          <Field label="Job title" name="title" className="sm:col-span-2" />
          <Field label="Site address" name="site_address" className="sm:col-span-2" />
          <Field label="Type" name="type" as="select">
            <option value="interior">Interior</option>
            <option value="exterior">Exterior</option>
            <option value="both">Interior and exterior</option>
          </Field>
          <Field label="Estimate due date" name="estimate_due_date" type="date" />
          <Field label="Requested start date" name="requested_start_date" type="date" />
          <Field label="Requested end date" name="requested_end_date" type="date" />
          <Field
            label="Important instructions"
            name="important_instructions"
            as="textarea"
            rows={2}
            className="sm:col-span-2"
          />
          <Field label="Notes" name="notes" as="textarea" rows={3} className="sm:col-span-2" />
        </div>
      </Section>

      <Section number="03" title="Areas and scope">
        <div className="flex flex-col gap-12">
          {areas.map((area, areaIndex) => (
            <div key={areaIndex}>
              <div className="flex items-end gap-4">
                <Field
                  label={`Area ${areaIndex + 1}`}
                  name="area_name"
                  placeholder="e.g. Living room, Front exterior"
                  className="flex-1"
                />
                {areas.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeArea(areaIndex)}
                    className="pb-2 text-[11px] tracking-[0.2em] text-gray-500 uppercase hover:text-danger"
                  >
                    Remove
                  </button>
                )}
              </div>

              {area.scope_items.map((_, itemIndex) => (
                <fieldset
                  key={itemIndex}
                  className="mt-8 grid gap-x-8 gap-y-6 border-l border-line pl-5 sm:grid-cols-2 sm:pl-8"
                >
                  <legend className="mb-4 text-[11px] tracking-[0.2em] text-gray-400 uppercase">
                    Scope item {itemIndex + 1}
                  </legend>
                  <Field
                    label="Description"
                    name="description"
                    placeholder="e.g. Walls and ceiling"
                    className="sm:col-span-2"
                  />
                  <Field label="Prep" name="prep" />
                  <Field label="Products" name="products" />
                  <Field label="Color" name="color" />
                  <Field label="Sheen" name="sheen" as="select">
                    <option value="">Select…</option>
                    <option value="flat">Flat</option>
                    <option value="eggshell">Eggshell</option>
                    <option value="satin">Satin</option>
                    <option value="semi_gloss">Semi-gloss</option>
                    <option value="gloss">Gloss</option>
                  </Field>
                  <Field label="Dimensions" name="dimensions" placeholder="e.g. 12 x 14 ft" />
                  <label className="flex items-center gap-3 text-sm sm:self-end sm:pb-2">
                    <input
                      type="checkbox"
                      name="included"
                      defaultChecked
                      className="size-4 accent-ink"
                    />
                    Included in scope
                  </label>
                </fieldset>
              ))}

              <button
                type="button"
                onClick={() => addScopeItem(areaIndex)}
                className="mt-6 ml-5 text-[11px] tracking-[0.2em] uppercase underline-offset-4 hover:underline sm:ml-8"
              >
                + Add scope item
              </button>
            </div>
          ))}

          <button
            type="button"
            onClick={addArea}
            className="border border-ink px-4 py-4 text-[11px] tracking-[0.25em] uppercase transition-colors hover:bg-ink hover:text-white"
          >
            + Add area
          </button>
        </div>
      </Section>

      {/* Full-width button on phones, normal size on desktop */}
      <button
        type="submit"
        className="w-full bg-ink px-10 py-4 text-xs tracking-[0.25em] text-white uppercase transition-opacity hover:opacity-80 sm:w-auto sm:self-end"
      >
        Save intake
      </button>
    </form>
  )
}
