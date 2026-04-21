/**
 * Filterbox allows you to use checkboxes to show and hide rows of data.
 *
 * To use it, you ensure that your HTML has a controls block. Note that if you omit the
 * id="" and for="" tags on the input and label, they will be inferred from the
 * label contents.  In the code below
 * - the first checkbox toggles "cats" (despite the label being "Felines")
 * - the second toggles "dogs" (inferred from the label)
 * - the third toggles "bugs", and ignores the explanatory text after the colon
 * - the fourth toggles "bugs", and ignores the explanatory text in parenthesis
 * - the fifth toggles "eight-legs" (8 became eight since CSS class names cannot begin with digits)
 * - the sixth toggles "birds-and-bees" (spaces become hyphens)
 * - the seventh toggles both "birds" and "Bees" (commas separate items)
 *
 * <ul class="filterbox-controls filter-animals">
 * <li><input type="checkbox" id="cats"><label for="cats">Felines</label></li>
 * <li><input type="checkbox"><label>Dogs</label></li>
 * <li><input type="checkbox"><label>Bugs: six-legged beasties</label></li>
 * <li><input type="checkbox"><label>Bugs (six-legged beasties)</label></li>
 * <li><input type="checkbox"><label>8-Legs (arachnids and octopi)</label></li>
 * <li><input type="checkbox"><label>Birds and Bees</label></li>
 * <li><input type="checkbox"><label>Birds, Bees</label></li>
 * </ul>
 *
 * Your HTML also must have a data block:
 *
 * <table class="filterbox-data filter-animals">
 * <th>...</th>
 * <tr class="cats">...</tr>
 * <tr class="cats">...</tr>
 * <tr class="dogs">...</tr>
 * <tr class="bugs">...</tr>
 * <tr class="eight-legs">...</tr>
 * <tr class="birds">...</tr>
 * <tr class="bees">...</tr>
 * <tr class="birds-and-bees">...</tr>
 * </table>
 *
 * When the user toggles the checkbox for a given id, all data elements with that
 * CSS class have their visibility toggled. In the case above if the user toggles
 * the last checkbox both the "birds" and "bees" rows will be hidden, but not the
 * "birds-and-bees" row.
 *
 * ***
 *
 * This filterbox.js file pairs very nicely with the checkbox-radio-group.js file which
 * will allow the user to command-click (or long-press) to toggle the visibility of all
 * items *except* the one they just selected, and with the stored-checkbox-state.js
 * file which preserves checkbox state across page-loads using local storage.
 *
 * If you do use these files you must include them *after* this file, so that this file's
 * setup will have created the checkbox html elements (and attached its event listeners)
 * before those files attempt to work with them.
 */
 
const filterboxBootstrap = () => {

/**
 * By default the script looks for combo values, but you can disable this if you
 * do not use combos and have a sufficiently-large data set that the search is
 * causing performance problems.
 *
 * A combo is a data class that contains more than one of the filtered values, e.g.,
 *      <div class="filterbox-controls filter-traits">
 *        <div><input type="checkbox"><label>Eggs</label></div>
 *        <div><input type="checkbox"><label>Lactation</label></div>
 *        <div><input type="checkbox"><label>Scales</label></div>
 *      </div>
 *      <ul class="filterbox-data">
 *        <li class="lactation">Cat<li>
 *        <li class="eggs">Robin<li>
 *        <li class="eggs lactation">Platypus<li>
 *        <li class="scales">Snake<li>
 *      </ul>
 *
 * Without looking for combos, checking "Eggs" and not "Lactation" will result
 * in both "Cat" and "Platypus" being hidden due to the simple CSS rules
 *      .filterbox-data.filter-traits.hide-eggs .eggs { display: none }
 *      .filterbox-data.filter-traits.hide-lactation .lactation { display: none }
 *      .filterbox-data.filter-traits.hide-scales .scales { display: none }
 *
 * With combos enabled, checking "Eggs" and not "Lactation" will reveal both
 * "Robin" and "Platypus" because of a more sophisticated set of rules
 *      .filterbox-data.filter-traits.hide-eggs.hide-lactations .eggs.lactation { display: none }
 *      .filterbox-data.filter-traits.hide-eggs .eggs:not(.eggs.lactation) { display: none }
 *      .filterbox-data.filter-traits.hide-lactation .lactation:not(.eggs.lactation) { display: none }
 *      .filterbox-data.filter-traits.hide-scales .scales { display: none }
 *
 * Note that checking "eggs" and unchecking "scales" hides the snake because the "Snake"
 * line item does not have the "eggs" css class (though it probably should). If it did,
 * then rules would have been constructed to handle that scenario as well.
 *
 * Unfortunately, the rules would not work and the snake would still be hidden. This is
 * a known bug -- the "hiding .lactation without .eggs.lactation" rule would hide the
 * snake.  At the moment if you are going to have combos no two combos can have
 * overlapping elements.
 */
const shouldLookForCombos = true

/**
 * Turn '3d' into 'three-d' and '32flavors' into 'three-two-flavors' since CSS class names
 * cannot begin with a digit.
 */
const digitsToWords = text => {
    return text
        .replace('0', 'zero-')
        .replace('1', 'one-')
        .replace('2', 'two-')
        .replace('3', 'three-')
        .replace('4', 'four-')
        .replace('5', 'five-')
        .replace('6', 'six-')
        .replace('7', 'seven-')
        .replace('8', 'eight-')
        .replace('9', 'nine-')
}

/**
 * Given '3 Musketeers' return 'three-musketeers'
 */
const textToCssClass = text => {
    return digitsToWords(text).replace(/\W+/, '-').toLocaleLowerCase()
}

/**
 * Adds a class to all filterbox-data containers to hide (or not hide) elements with
 * the given filtered values for a given filter-value type. e.g. given 'animal', 'cat',
 * and 'false', it will turn
 *    <div class="filterbox-data animal">
 * into
 *    <div class="filterbox-data animale hide-cat">
 * so that the CSS rules will hide all <div class="cat"> child elements.
 */
const setVisibility = (filterType, filterClassName, flag) => {
    const targetClassName = `filterbox-data ${filterType}`
    const filterContainers = document.getElementsByClassName(targetClassName)
    if (!filterContainers.length) {
        console.error(`no element with class="${targetClassName}"`)
        return
    }
    for (container of filterContainers) {
        for (filterValue of filterClassName.split(' ')) {
            filterValue = digitsToWords(filterValue)
            const className = container.getAttribute('class') || ''
            const hiddenPart = `hide-${filterValue}`
            const parts = className.split(' ').filter(x => x != hiddenPart)
            if (!flag) {
                parts.push(hiddenPart)
            }
            container.setAttribute('class', parts.join(' '))
        }
    }
}

/**
 * Given an HTML container element, decorate any <input type="checkbox"> elements with
 * change-event listeners that will toggle the visibility of corresponding data elements
 * in any filterbox-data containers.
 *
 * The passed cssRules array will be populated with CSS rules that should be injected
 * into the document's <head> to actually accomplish the visibility changes.
 */
const wireUpFilterControlContainer = (container, cssRules) => {
    const filterType = container.getAttribute('class').split(' ').filter(x => x.startsWith('filter-'))[0]
    if (!filterType) {
        console.error('filterbox-controls lacks a filter-TYPE class:', container)
        return
    }
    var filterableValues = []
    const toggles = container.getElementsByTagName('input')
    for (toggle of toggles) {
        const toggleId = toggle.getAttribute('id')
        const label = toggle.nextElementSibling
        const filterValues = toggleId
            ? [toggleId]
            : label.innerHTML
                .replace(/<span class="text">(.*?)<\/span>\s*/m, '$1')
                .replace(/<span class="icon">(.*?)<\/span>\s*/m, '')
                .toLocaleLowerCase()
                .replace(/ *[(].*[)]/, '')
                .replace(/:.*/, '')
                .split(/, */)
                .map(x => x.replace(/\W+/g, ' ').trim().replace(/ /g, '-'))
        filterableValues.push(...filterValues)
        const filterId = `${filterType}-${filterValues.join('-')}`
        const filterClassName = filterValues.join(' ')
        if (!toggleId) { toggle.setAttribute('id', filterId) }
        if (!toggle.getAttribute('class')) { toggle.setAttribute('class', filterClassName) }
        const stateChange = event => {
            setVisibility(filterType, filterClassName, event.target.checked)
        }
        label.setAttribute('for', toggleId || filterId)
        toggle.addEventListener('change', stateChange)
        toggle.checked = true
    }
    if (shouldLookForCombos) {
        const combos = new Set() // e.g., {'audio & video', 'photo & video'}
        const classes = new Set(filterableValues.map(textToCssClass))
        for (dataContainer of document.getElementsByClassName('filterbox-data')) {
            for (dataElement of dataContainer.children) {
                const cssClass = dataElement.getAttribute('class') || ''
                const classNames = cssClass.split(/ +/).filter(s => classes.has(s))
                if (classNames.length > 1) {
                    const sortedClassNames = classNames.sort()
                    combos.add(sortedClassNames.join(' & '))
                }
            }
        }
        const comboArrays = Array.from(combos).sort().map(c => c.split(' & ')) // e.g., [['audio', 'video'], ['photo', 'video']]
        const comboValues = new Set(comboArrays.flat()) // e.g., {'audio', 'photo', 'video'}
        for (filterValue of filterableValues.filter(v => !comboValues.has(v))) {
            filterValue = textToCssClass(filterValue)
            cssRules.push(`.filterbox-data.${filterType}.hide-${filterValue} .${filterValue} { display: none }`)
        }
        for (combo of comboArrays) {
            const comboClass = combo.join('.')
            const hideClasses = combo.map(v => `.hide-${v}`).join('')
            cssRules.push(`.filterbox-data.${filterType}${hideClasses} .${comboClass} { display: none }`)
            for (filterValue of combo) {
                cssRules.push(`.filterbox-data.${filterType}.hide-${filterValue} .${filterValue}:not(.${comboClass}) { display: none }`)
            }
        }
    } else {
        for (filterValue of filterableValues) {
            filterValue = textToCssClass(filterValue)
            cssRules.push(`.filterbox-data.${filterType}.hide-${filterValue} .${filterValue} { display: none }`)
        }
    }
}

/**
 * Locates all HTML container elements with class 'filterbox-controls' and wires up the
 * checkboxes within them as visibility controls.
 */
const wireUpAllFilterControlContainers = () => {
    const cssRules = []
    const filterControlContainers = document.getElementsByClassName('filterbox-controls')
    for (container of filterControlContainers) {
        wireUpFilterControlContainer(container, cssRules)
    }
    const head = document.getElementsByTagName('head')[0]
    const style = document.createElement('style')
    style.setAttribute('type', 'text/css')
    style.innerHTML = cssRules.join('\n')
    head.appendChild(style)
}

window.addEventListener('load', wireUpAllFilterControlContainers)
 
}
filterboxBootstrap()
